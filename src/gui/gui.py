from nicegui import ui

from src.core.mods.filter_logic import FilterLogic
from src.core.subjects.filters_handler import FiltersHandler
from src.core.subjects.filters_iterator import FiltersIterator
from src.core.subjects.subject_creator import SubjectCreator
from src.gui.gui_handler import GuiHandler
from src.gui.widgets import (
    FileModWidget,
    FolderModWidget,
    LocalFolderPicker,
    SearchWidget,
)


class GenericFileFilter:
    def __init__(self):
        self.src_path = None
        self.dst_path = None

        self.expand = {'search': True, 'file_modifications': True, 'folder_modifications': True}

        self.gui_handler = GuiHandler()
        self.filter_logic = FilterLogic()
        self.filters_handler = FiltersHandler()

        self.search_widget = SearchWidget()
        self.file_mod_widget = FileModWidget()
        self.folder_mod_widget = FolderModWidget()

    def __call__(self):
        self.header()
        self.left_drawer()
        self.tree_view()

    def header(self):
        with ui.header():
            ui.label('Cleaner').style('font-size: 30px; font-weight: bold; color: #3874c8;')

    @ui.refreshable
    def left_drawer(self):
        with ui.left_drawer().classes('bg-blue-100 w-full h-full').props('width=400'):
            ui.button('Set Source', icon='input', on_click=self.pick_source).classes('w-full')

            if self.gui_handler.original:
                with ui.expansion(
                    'Search',
                    icon='search',
                    value=self.expand['search'],
                    on_value_change=lambda e: self.expand.update({'search': e.value}),
                ).classes('w-full'):
                    self.search_widget.get_widget(self.process_search)

            if self.gui_handler.search:
                with ui.expansion(
                    'File Modifications',
                    icon='description',
                    value=self.expand['file_modifications'],
                    on_value_change=lambda e: self.expand.update({'file_modifications': e.value}),
                ).classes('w-full'):
                    self.file_mod_widget.get_widget()
                    ui.button('Apply', on_click=self.process_file_mods)

            if self.gui_handler.file_modifications:
                with ui.expansion(
                    'Folder Modifications',
                    value=self.expand['folder_modifications'],
                    icon='folder',
                    on_value_change=lambda e: self.expand.update({'folder_modifications': e.value}),
                ).classes('w-full'):
                    self.folder_mod_widget.get_widget()
                    ui.button('Apply', on_click=self.process_folder_mods)

            if self.gui_handler.folder_modifications:
                with ui.expansion('Final', icon='file_download', value=True, on_value_change=None).classes('w-full'):
                    ui.button('Set Destination', icon='output', on_click=self.pick_destination).classes('w-full')

                    if self.dst_path:
                        ui.button('Export', icon='play_arrow', on_click=self.execute).classes('w-full')
                    else:
                        ui.button('Export', icon='play_arrow', on_click=self.execute).classes('w-full').props('hidden')

    def tree_view(self):
        """Tree view"""
        with ui.row().classes('w-full h-full no-wrap'):
            self.show_gui_tree('original')
            self.show_gui_tree('search')
            self.show_gui_tree('file_modifications')
            self.show_gui_tree('folder_modifications')

    def process_search(self):
        """Process filters"""
        filters_iter, collisions, inactive = self.filter_logic.apply_search(self.filters_handler)

        if filters_iter is None:
            ui.notify('The filters must first be defined before they can be applied', type='info')
            return None

        if collisions:
            with ui.dialog().classes('no-wrap') as collision_dialog, ui.card():
                collision_dialog.open()
                ui.label('Filter collisions:').style('font-size: 20px; font-weight: bold; color: #3874c8')
                with ui.scroll_area().style('height: 500px; width: 500px;'):
                    for filter_names in collisions:
                        ui.label(f'{filter_names}, here a subset of collisions:').style(
                            'font-size: 20px; font-weight: bold;'
                        )
                        for collision in collisions[filter_names]:
                            ui.label(collision).style('font-size: 15px; font-weight: bold;')
                ui.button('Close', on_click=collision_dialog.close)
            return None

        if inactive:
            with ui.dialog() as inactive_dialog, ui.card():
                inactive_dialog.open()
                ui.label('Inactive Filter:').style('font-size: 20px; font-weight: bold; color: #3874c8').classes(
                    'w-full'
                )
                for filter_name in inactive:
                    ui.label(filter_name).style('font-size: 15px; font-weight: bold;')
                ui.button('Close', on_click=inactive_dialog.close)
            return None

        self.filters_handler.set('search', filters_iter)
        self.update_state(self.filters_handler, 'search', 'file_path_rel')

    def process_file_mods(self):
        """Process file modifications"""
        filters_iter = self.filter_logic.apply_file_modifications(self.filters_handler)

        if filters_iter is None:
            ui.notify('The modifications must first be defined before they can be applied', type='info')
            return None

        self.filters_handler.set('file_modifications', filters_iter)
        self.expand.update({'search': False})
        self.update_state(self.filters_handler, 'file_modifications', 'new_file_path_rel')

    def process_folder_mods(self):
        filters_iter = self.filter_logic.apply_folder_modifications(self.filters_handler)

        if filters_iter is None:
            ui.notify('The modifications must first be defined before they can be applied', type='info')
            return None

        self.filters_handler.set('folder_modifications', filters_iter)
        self.expand.update({'file_modifications': False})
        self.update_state(self.filters_handler, 'folder_modifications', 'new_file_path_rel')

    async def pick_source(self) -> None:
        """Pick source folder"""

        src_path = await LocalFolderPicker('~')

        if src_path is None:
            return None

        subject_creator = SubjectCreator(src_path)
        subject_iter = subject_creator()
        filters_iter = FiltersIterator(original=subject_iter)
        self.filters_handler.set(state='original', filters_iter=filters_iter)

        if len(subject_iter) == 0:
            ui.notify(f'No files found in {src_path}', type='negative')
            return None

        if len(subject_iter) >= 10000:
            ui.notify(
                "To many files to show, only the first 10'000 are presented here."
                f"However, all of the files in {self.src_path} will be processed.",
                type='ongoing',
                multi_line=True,
                close_button='OK',
            )

        self.src_path = src_path
        self.update_state(self.filters_handler, 'original', 'file_path_rel')

    def update_state(self, subject_handler, state, path_type):
        self.gui_handler.subject_handler_to_gui_handler(subject_handler, state, path_type)
        self.show_gui_tree.refresh()
        self.left_drawer.refresh()

    async def pick_destination(self) -> None:
        """Pick destination folder"""

        self.dst_path = await LocalFolderPicker('~')
        if self.dst_path is None:
            return None

        ui.notify(f'Your output will be in {self.dst_path}')
        self.left_drawer.refresh()

    def execute(self):
        """Execute the file modifications"""
        if self.dst_path is None:
            ui.notify('You must first set the destination folder', type='info')
            return None

        self.filter_logic.apply_new_structure(self.filters_handler, self.dst_path)
        ui.notify(f'Copied files to new structure in {self.dst_path}', type='positive')

    def tree_menu(self, state):
        """Tree menu"""

        def tree_filter(e, _state):
            if e.value == '':
                getattr(self.gui_handler, state).tree_gui._props['filter'] = ''
            else:
                getattr(self.gui_handler, state).tree_gui._props['filter'] = e.value
            getattr(self.gui_handler, state).tree_gui.expand()

        tree_name = state.replace('_', ' ').capitalize()
        ui.label(tree_name).style('font-size: 20px; font-weight: bold; color: #3874c8')
        with ui.row().classes('w-full no-wrap'):
            ui.input('Search', on_change=lambda e, _state=state: tree_filter(e, _state))
            ui.button(
                icon='expand_more',
                on_click=lambda e: getattr(self.gui_handler, state).tree_gui.props('filter=').expand(),
            )
            ui.button(
                icon='expand_less',
                on_click=lambda e: getattr(self.gui_handler, state).tree_gui.props('filter=').collapse(),
            )

    @ui.refreshable
    def show_gui_tree(self, state) -> None:
        """Show gui tree"""
        if getattr(self.gui_handler, state):
            with ui.column().classes('w-full h-full no-wrap'):
                self.tree_menu(state)
                with ui.scroll_area().style('height: 1000px;'):
                    tree = ui.tree(getattr(self.gui_handler, state).tree_format, label_key='id').expand()
                    del tree._props['selected']
                    getattr(self.gui_handler, state).tree_gui = tree
