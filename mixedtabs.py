import sublime
import sublime_plugin
import re

class MixedTabs(sublime_plugin.EventListener):
    # shared_instance = None

    # @classmethod
    # def shared_plugin(cls):
    #     return cls.shared_instance

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.__class__.shared_instance = self

    # Public API

    @classmethod
    def get_unmodified(cls, view):
        if is_mixed_tabs(view):
            return Unexpand.transformed(view)
        else:
            return whole(view)

    # Event listeners

    def on_load(self, view):
        view.run_command("mixed_tabs_load")

    def on_pre_save(self, view):
        view.run_command("mixed_tabs_pre_save")

    def on_post_save(self, view):
        view.run_command("mixed_tabs_post_save")

    def on_window_command(self, window, command_name, args):
        # TODO: Only do this if last command was post_save
        if command_name == 'close':
            last_command = window.active_view().command_history(0, True)
            if last_command[0] == 'mixed_tabs_post_save':
                window.active_view().run_command('undo')

class MixedTabsLoad(sublime_plugin.TextCommand):
    def run(self, edit):
        if is_mixed_tabs(self.view):
            Expand.replace(edit, self.view)

class MixedTabsPreSave(sublime_plugin.TextCommand):
    def run(self, edit):
        if is_mixed_tabs(self.view):
            Store.backup(self.view)
            Unexpand.replace(edit, self.view)

class MixedTabsPostSave(sublime_plugin.TextCommand):
    def run(self, edit):
        if Unexpand.pop_replaced(self.view):
            Store.restore(edit, self.view)

##############################################################################

def is_mixed_tabs(view):
    return view.substr(whole(view)).startswith('// :mixed_tabs')

class Expand(object):
    @staticmethod
    def replace(edit, view):
        original = view.substr(whole(view))
        modified = original.expandtabs(8)
        view.replace(edit, whole(view), modified)

class Unexpand(object):
    view_ids = set()

    @classmethod
    def transformed(cls, view):
        original = view.substr(whole(view))

        modified = ''
        for line in original.split('\n'): # TODO: Do this lazily for performance?
            indent, rest = re.match(r'^( *)(.*)$', line).group(1, 2)
            modified += indent.replace(' ' * 8, '\t')
            modified += rest + '\n'
        return modified[:-1] # don't add an additional newline at the end

    @classmethod
    def replace(cls, edit, view):
        """Replaces the view and marks it as replaced."""
        modified = cls.transformed(view)

        # Need to change the setting because otherwise Sublime translates my
        # hard-gained tabs into spaces on-the-fly.
        view.settings().set('translate_tabs_to_spaces', False)
        view.replace(edit, whole(view), modified)
        view.settings().set('translate_tabs_to_spaces', True)
        cls.view_ids.add(view.id())

    @classmethod
    def pop_replaced(cls, view):
        """Returns whether or not the view was replaced and unmarks the view."""
        if view.id() in cls.view_ids:
            cls.view_ids.remove(view.id())
            return True
        else:
            return False

class Store(object):
    content = {}
    viewport_position = {}
    selection = {}

    @classmethod
    def backup(cls, view):
        cls.content[view.id()] = view.substr(whole(view))
        cls.viewport_position[view.id()] = view.viewport_position()
        cls.selection[view.id()] = list(view.sel())

    @classmethod
    def restore(cls, edit, view):
        view.replace(edit, whole(view), cls.content[view.id()])
        view.set_viewport_position(cls.viewport_position[view.id()], False)
        view.sel().clear()
        view.sel().add_all(cls.selection[view.id()])

        del cls.content[view.id()]
        del cls.viewport_position[view.id()]
        del cls.selection[view.id()]

def whole(view):
    return sublime.Region(0, view.size())
