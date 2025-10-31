from ui.page import Page


class Chat(Page):
    def __init__(self, infobar_contents, menubar_labels, messages):
        super().__init__()
        self.create_infobar(infobar_contents)

        self.create_content()
        self.add_message_rows(len(messages))
        self.populate_message_rows(messages)

        self.create_menubar(menubar_labels)
