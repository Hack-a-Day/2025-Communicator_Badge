import lvgl


def create_image(filename, parent=None):
    parent = parent or lvgl.screen_active()
    image = lvgl.image(parent)
    with open(filename, "rb") as f:
        image_data = f.read()
    image_dsc = lvgl.image_dsc_t({"data_size": len(image_data), "data": image_data})
    image.set_src(image_dsc)
    return image
