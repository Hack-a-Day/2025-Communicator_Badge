# ugit
# micropython OTA update from github
# Created by TURFPTAx for the openmuscle project
# Check out https://openmuscle.org for more info
#
# Pulls files and folders from open github repository
# Updated: scoped to a specific subfolder in the repo and maps it to device root,
# and uses Git blob SHA to skip identical files.

import os
import urequests
import json
import hashlib
import binascii
import machine
import time
import network

# ------------------------- User Variables ------------------------- #
# Default Network to connect using wificonnect()
ssid = "Supercon"
password = "whatpassword"

# CHANGE TO YOUR REPOSITORY INFO
# Repository must be public if no personal access token is supplied
user = 'Hack-a-Day'
repository = '2025-Communicator_Badge'
token = ''

# Default branch for both API and raw content
default_branch = 'main'

# The subfolder inside the repo to sync to device root.
# Example: "firmware/badge" => repo:/firmware/badge/** -> device:/**
repo_subdir = 'firmware/badge'  # no leading slash, no trailing slash preferred

# Don't remove ugit.py from the ignore_files unless you know what you are doing :D
# Paths in this list are compared as device paths with a leading '/', e.g. '/ugit.py'
ignore_files = ['/ugit.py']
ignore = ignore_files
# ----------------------- END USER VARIABLES ----------------------- #

# Normalize repo_subdir once
repo_subdir = (repo_subdir or '').strip('/')

# Static URLs (use default_branch for both API & raw)
giturl = 'https://github.com/{user}/{repository}'
call_trees_url = 'https://api.github.com/repos/{user}/{repository}/git/trees/{branch}?recursive=1'.format(
    user=user, repository=repository, branch=default_branch
)
raw = 'https://raw.githubusercontent.com/{user}/{repository}/{branch}/'.format(
    user=user, repository=repository, branch=default_branch
)

# Internal globals / constants
internal_tree = []
_manifest_path = '/.ugit_managed'  # newline-separated list of managed local file paths (no leading slash)


# ----------------------------- Helpers ---------------------------- #
def _starts_with_repo_subdir(path):
    """True if repo path is under the selected subdir (or all if subdir unset)."""
    if not repo_subdir:
        return True
    return path == repo_subdir or path.startswith(repo_subdir + '/')

def _repo_to_local(path):
    """
    Map 'firmware/badge/some/dir/file.py' -> 'some/dir/file.py'
    If path equals the subdir itself, return '' (caller should skip).
    If no repo_subdir set, returns path as-is.
    """
    if not repo_subdir:
        return path
    if path == repo_subdir:
        return ''
    return path[len(repo_subdir) + 1:]  # drop 'repo_subdir/'

def _ensure_parent_dirs(local_path):
    """
    Create parent directories for local_path if needed.
    MicroPython has no os.makedirs, so walk the parts.
    Accepts either 'x/y/z.py' or '/x/y/z.py'.
    """
    p = local_path[1:] if local_path.startswith('/') else local_path
    parts = p.split('/')
    if len(parts) <= 1:
        return
    cur = ''
    for seg in parts[:-1]:
        if not seg:
            continue
        cur = (cur + '/' + seg) if cur else seg
        d = '/' + cur
        try:
            os.mkdir(d)
        except OSError:
            # already exists or cannot create
            pass

def _normalize_local_lead(path_no_lead):
    """Ensure a leading slash for comparing against ignore list."""
    return path_no_lead if path_no_lead.startswith('/') else '/' + path_no_lead

def _write_manifest(paths_no_lead):
    try:
        with open(_manifest_path, 'w') as f:
            for p in paths_no_lead:
                f.write(p + '\n')
    except:
        pass

def _read_manifest():
    paths = []
    try:
        with open(_manifest_path, 'r') as f:
            for line in f:
                p = line.strip()
                if p:
                    paths.append(p)
    except:
        pass
    return paths

def _lower(s):
    try:
        return s.lower()
    except:
        return s

def _git_blob_sha1_of_file(local_path_no_lead):
    """
    Compute Git blob SHA1 for the *local file* at '/<local_path_no_lead>'.
    Formula: sha1( b'blob {size}\\0' + file_bytes )
    Returns the lowercase hex string, or '' if not found/readable.
    """
    try:
        full = '/' + local_path_no_lead if not local_path_no_lead.startswith('/') else local_path_no_lead
        st = os.stat(full)
        size = st[6]  # file size in bytes
        h = hashlib.sha1()
        header = b'blob ' + str(size).encode('utf-8') + b'\x00'
        h.update(header)
        with open(full, 'rb') as f:
            while True:
                chunk = f.read(2048)
                if not chunk:
                    break
                h.update(chunk)
        return binascii.hexlify(h.digest()).decode('utf-8')
    except:
        return ''


# --------------------------- Core Functions --------------------------- #
def pull(local_path, remote_repo_path):
    """
    Fetch a single file from GitHub and write to local_path.
    Tries text write first; if decoding fails, writes raw bytes.
    local_path should include leading slash.
    """
    print('pulling {} -> {}'.format(remote_repo_path, local_path))
    headers = {'User-Agent': 'ugit-turfptax'}
    if len(token) > 0:
        headers['authorization'] = "bearer %s" % token

    raw_url = raw + remote_repo_path
    r = urequests.get(raw_url, headers=headers)
    try:
        content = r.content
    finally:
        try:
            r.close()
        except:
            pass

    _ensure_parent_dirs(local_path)

    # Try text mode
    try:
        with open(local_path, 'w') as new_file:
            new_file.write(content.decode('utf-8'))
        return
    except:
        pass

    # Fallback to binary write
    try:
        with open(local_path, 'wb') as new_file:
            new_file.write(content)
    except:
        print('Failed to write file (binary). Consider ignoring non-text assets in the repo_subdir.')

def pull_all(tree=call_trees_url, raw=raw, ignore=ignore, isconnected=False):
    if not isconnected:
        wificonnect()

    os.chdir('/')

    # Pull Git tree
    tree = pull_git_tree()

    # Build filtered lists from tree entries (we need entry['sha'] for comparisons)
    filtered_entries = []  # list of dicts for blobs in repo_subdir
    filtered_dirs = []     # list of repo directory paths in repo_subdir
    intended_local_files = []  # local paths (no leading slash) that are managed

    for entry in tree.get('tree', []):
        p = entry.get('path', '')
        t = entry.get('type', '')
        if not _starts_with_repo_subdir(p):
            continue
        if t == 'tree':
            filtered_dirs.append(p)
        elif t == 'blob':
            local_path = _repo_to_local(p).strip('/')
            if not local_path:
                continue
            local_path_with_lead = _normalize_local_lead(local_path)
            if local_path_with_lead in ignore:
                continue
            filtered_entries.append(entry)  # keep full entry (includes 'sha')
            intended_local_files.append(local_path)

    # Create local dirs needed (based on filtered_dirs)
    for repo_dir in filtered_dirs:
        local_dir = _repo_to_local(repo_dir).strip('/')
        if not local_dir:
            continue
        # Create parent chain by faking a filename
        try:
            _ensure_parent_dirs('/' + local_dir + '/.d')
        except:
            pass
    
    # Read previous manifest to compute scoped deletions later
    prev_manifest = set(_read_manifest())

    # Download/update files (skip identical by comparing Git blob SHA)
    log = []
    for entry in filtered_entries:
        repo_path = entry['path']
        local_path = _repo_to_local(repo_path).strip('/')
        if not local_path:
            continue

        local_path_with_lead = _normalize_local_lead(local_path)
        if local_path_with_lead in ignore:
            continue

        remote_blob_sha = _lower(entry.get('sha', ''))
        local_blob_sha = _git_blob_sha1_of_file(local_path)

        if local_blob_sha and (local_blob_sha == remote_blob_sha):
            # identical — skip pulling
            log.append(local_path + ' unchanged (skipped)')
            continue

        # Otherwise, update the file
        abs_local = '/' + local_path if not local_path.startswith('/') else local_path
        try:
            try:
                os.remove(abs_local)
                log.append(local_path + ' removed before update')
            except:
                pass
            pull(abs_local, repo_path)
            log.append(local_path + ' updated')
        except Exception as e:
            log.append(local_path + ' failed to pull: {}'.format(e))

    # Compute leftovers safely: only remove files that we previously managed
    curr_manifest = set(intended_local_files)
    leftovers = prev_manifest - curr_manifest

    if leftovers:
        print('Removing leftovers from previous sync:', leftovers)
        for lf in leftovers:
            try:
                os.remove('/' + lf if not lf.startswith('/') else lf)
                log.append(lf + ' removed (leftover)')
            except:
                log.append(lf + ' failed to remove (leftover)')

    # Persist new manifest
    _write_manifest(intended_local_files)

    # Log and reboot
    try:
        with open('/ugit_log.py', 'w') as logfile:
            logfile.write(str(log))
    except:
        pass

    print('>>>>> uGit pull_all complete! <<<<<<')
    time.sleep(1)
    print('resetting machine: machine.reset()')
    machine.reset()

def wificonnect(ssid=ssid, password=password):
    print('Use: ugit.wificonnect(SSID, Password) or relies on config at top of ugit.py')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        pass
    print('Wifi Connected!!')
    print('SSID:', ssid)
    print('Local IP, Subnet, Gateway, DNS:')
    print(wlan.ifconfig())
    return wlan

def build_internal_tree():
    global internal_tree
    internal_tree = []
    os.chdir('/')
    for i in os.listdir():
        add_to_tree(i)
    return internal_tree

def add_to_tree(dir_item):
    global internal_tree
    if is_directory(dir_item) and len(os.listdir(dir_item)) >= 1:
        os.chdir(dir_item)
        for i in os.listdir():
            add_to_tree(i)
        os.chdir('..')
    else:
        if os.getcwd() != '/':
            subfile_path = os.getcwd() + '/' + dir_item
        else:
            subfile_path = os.getcwd() + dir_item
        try:
            internal_tree.append([subfile_path, get_hash(subfile_path)])
        except OSError:
            print('{} could not be added to tree'.format(dir_item))

def get_hash(file):
    try:
        with open(file, 'r') as o_file:
            r_file = o_file.read()
        # sha1 requires bytes
        sha1obj = hashlib.sha1(r_file.encode('utf-8'))
        h = sha1obj.digest()
        return binascii.hexlify(h)
    except:
        return b''

def get_data_hash(data):
    sha1obj = hashlib.sha1(data)
    h = sha1obj.digest()
    return binascii.hexlify(h)

def is_directory(file):
    try:
        return (os.stat(file)[8] == 0)
    except:
        return False

def pull_git_tree(tree_url=call_trees_url, raw=raw):
    headers = {'User-Agent': 'ugit-turfptax'}
    if len(token) > 0:
        headers['authorization'] = "bearer %s" % token
    r = urequests.get(tree_url, headers=headers)
    try:
        data = json.loads(r.content.decode('utf-8'))
    finally:
        try:
            r.close()
        except:
            pass

    if 'tree' not in data:
        print('\nDefault branch "{}" not found. Set "default_branch" variable to your default branch.\n'.format(default_branch))
        raise Exception('Default branch {} not found.'.format(default_branch))
    return data

def parse_git_tree():
    tree = pull_git_tree()
    dirs = []
    files = []
    for i in tree['tree']:
        if i['type'] == 'tree':
            dirs.append(i['path'])
        if i['type'] == 'blob':
            files.append([i['path'], i['sha'], i['mode']])
    print('dirs:', dirs)
    print('files:', files)

def check_ignore(tree=call_trees_url, raw=raw, ignore=ignore):
    os.chdir('/')
    tree = pull_git_tree()
    for i in tree['tree']:
        # remap to local path space and then compare with ignore
        local_path = _repo_to_local(i['path']).strip('/')
        if not local_path:
            continue
        local_path_with_lead = _normalize_local_lead(local_path)
        if local_path_with_lead in ignore:
            print(local_path_with_lead + ' is in ignore')
        else:
            print(local_path_with_lead + ' not in ignore')

def remove_ignore(internal_tree, ignore=ignore):
    # Kept for backward compatibility; now ignore is handled on mapped local paths
    clean_tree = []
    int_tree = []
    for i in internal_tree:
        int_tree.append(i[0])
    for i in int_tree:
        if i not in ignore:
            clean_tree.append(i)
    return clean_tree

def remove_item(item, tree):
    culled = []
    for i in tree:
        if item not in i:
            culled.append(i)
    return culled

def update():
    print('updates ugit.py to newest version from original ugit repo (turfptax)')
    raw_url = 'https://raw.githubusercontent.com/turfptax/ugit/master/'
    pull('/ugit.py', 'ugit.py')  # local refresh with our current logic
    # Note: If you truly want upstream, uncomment next line and comment the one above.
    # pull('/ugit.py', raw_url + 'ugit.py')

def backup():
    int_tree = build_internal_tree()
    backup_text = "ugit Backup Version 1.0\n\n"
    for i in int_tree:
        try:
            with open(i[0], 'r') as data:
                backup_text += 'FN:SHA1{},{}\n'.format(i[0], i[1])
                backup_text += '---' + data.read() + '---\n'
        except:
            pass
    try:
        with open('/ugit.backup', 'w') as backup_f:
            backup_f.write(backup_text)
    except:
        pass
