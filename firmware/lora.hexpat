#pragma author artemy
#pragma description Hackaday Supercon 2025 Communicator Badge LoRa packets parser
#pragma endian big

import std.io;
import std.mem;
import std.hash;
import type.base;
import type.magic;
import type.size;
import type.fmt;

bitfield Flags {
  reserved: 4;
  ttl: 4;
};

enum Port: u8 {
  Ping = 0x01,
  Pong = 0x02,
  ConfigOverride = 0x04,
  TextChat = 0x06,
  SignedTextChat = 0x07
};

struct Ping {
    type::Hex<u32> address;
    u8 counter;
};

struct Pong {
    type::Hex<u32> address;
    u8 ttl;
    u8 counter;
    float last_rssi;
    float last_snr;
};

struct ConfigOverride {
    u8 signature[128];
    char key[20];
    char value[80];
};

struct TextChat {
    type::Formatted<u16, "{:04d}"> channel;
    char source_alias[10];
    char text[100];
};

struct SignedTextChat {
    type::Formatted<u16, "{:04d}"> channel;
    char source_alias[10];
    u8 signature[128];
    char text[90];
};

fn validate_checksum(u16 stored_checksum, ref auto payload) {
    u16 calculated = std::hash::crc16(payload,  0x0000,  0x1021,  0x0000, false, false);

    if (calculated == stored_checksum) {
        std::print("Checksum valid: 0x{:04X}", stored_checksum);
        return true;
    } else {
        std::print("Checksum INVALID: stored=0x{:04X}, calculated=0x{:04X}", 
                   stored_checksum, calculated);
        return false;
    }
};

struct Packet {
     type::Magic<"\x07\xE9"> header;
     type::Hex<u16> checksum [[color("FF0000")]];
     Flags flags;
     type::Size<u8> length;
     // start counting the payload from length (one byte back)
     u8 payload_for_checksum[length - $] @ $-1 [[no_unique_address,hidden]];
     type::Hex<u32> destination;
     type::Hex<u32> source;
     Port port;
     u8 seq;

     if (length > 16) {
        match (port) {
            (Port::Ping): Ping ping;
            (Port::Pong): Pong pong;
            (Port::ConfigOverride): ConfigOverride config_override;
            (Port::TextChat): TextChat text_chat;
            (Port::SignedTextChat): SignedTextChat signed_text_chat;
            (_): u8 payload[length - 16];
        } 
    }
    bool checksum_valid = validate_checksum(checksum, payload_for_checksum) [[hidden]];
}[[name(port)]];

Packet packet @ 0x00;