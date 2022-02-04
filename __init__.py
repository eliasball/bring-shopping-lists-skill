from inspect import trace
from mycroft import MycroftSkill, intent_handler
from python_bring_api.bring import Bring
import traceback
from datetime import datetime, timedelta

class BringShoppingLists(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def initialize(self):
        self.settings_change_callback = self.on_settings_changed
        self.on_settings_changed()

    def on_settings_changed(self):
        try:
            self.listUuid = ''
            self.listName = ''
            self.loggedInUntil = None
            self.bring = Bring(self.settings.get('email', ''), self.settings.get('password', ''))
            if self.validate_login():
                self.log.debug('Bring! login successful!')
                self.fetch_active_list()
        except:
            self.log.exception(traceback.format_exc())

    def validate_login(self):
        """"
        Returns True if logged in and tries to login otherwise.
        Returns False if login failed.
        """
        if self.loggedInUntil == None:
            try:
                r = self.bring.login()
                if r.status_code == 200:
                    self.loggedInUntil = datetime.now() + timedelta(minutes=90)
                    return True
                else:
                    raise Exception(f'Login failed with status code {r.status_code}')
            except:
                self.log.exception(traceback.format_exc())
                return False
        
        if self.loggedInUntil < datetime.now():
            try:
                r = self.bring.login()
                if r.status_code == 200:
                    self.loggedInUntil = datetime.now() + timedelta(minutes=90)
                    return True
                else:
                    raise Exception(f'Login failed with status code {r.status_code}')
            except:
                self.log.exception(traceback.format_exc())
                return False
        else:
            return True

    def fetch_active_list(self):
        """
        Tries to set the active list to the one saved in settings.
        Returns True if uuid and name could be set.
        Returns False otherwise.
        """
        activeListName = self.settings.get('active_list').lower()
        lists = self.get_lists()
        if lists == []:
            return False

        if activeListName == None:
            self.listUuid = lists[0].get('listUuid')
            self.listName = lists[0].get('name')
            return True

        for list in lists:
            if list.get('name').lower() == activeListName:
                self.listUuid = list.get('listUuid')
                self.listName = list.get('name')
                return True
        return False

    def get_lists(self):
        """
        Tries to get an array of lists from bring.
        Returns empty array when unsuccessful.
        """
        if self.validate_login():
            try:
                return self.bring.loadLists()['lists']
            except:
                self.log.exception('Could not load lists from Bring:\n' + traceback.format_exc())
                return []
        return []
        

    @intent_handler('add.to.shopping.list.intent')
    def add_to_shopping_list(self, message):
        if self.validate_login():
            item = message.data.get('item').capitalize()
            listName = message.data.get('list_name')

            if listName == None:
                try:
                    if not self.fetch_active_list(): 
                        self.speak_dialog('could.not.find.any.list')
                        return
                    self.bring.saveItem(self.listUuid, item)
                    self.speak_dialog('item.was.added', {'item': item, 'list': self.listName})
                except:
                    self.log.exception('Could not add item to list:\n' + traceback.format_exc())
                    self.speak_dialog('error.adding.item', {'item': item, 'list': self.listName})
            else:
                lists = self.get_lists()
                if lists == []:
                    self.speak_dialog('could.not.find.any.list')
                    return
                
                for list in lists:
                    if list.get('name').lower() == listName.lower():
                        try:
                            self.bring.saveItem(list.get('listUuid'), item)
                            self.speak_dialog('item.was.added', {'item': item, 'list': list.get('name')})
                            return
                        except:
                            self.log.exception(f'Could not add item to list {listName}:\n' + traceback.format_exc())
                            self.speak_dialog('error.adding.item', {'item': item, 'list': listName})
                            return
                        

                self.speak_dialog('list.not.recognized', {'input': listName})
            
        else:
            self.speak_dialog('not.logged.in')


    @intent_handler('remove.from.shopping.list.intent')
    def remove_from_shopping_list(self, message):
        if self.validate_login():
            item = message.data.get('item').capitalize()
            listName = message.data.get('list_name')

            if listName == None:
                try:
                    if not self.fetch_active_list(): 
                        self.speak_dialog('could.not.find.any.list')
                        return
                    self.bring.removeItem(self.listUuid, item)
                    self.speak_dialog('item.was.removed', {'item': item, 'list': self.listName})
                except:
                    self.log.exception('Could not remove item from list:\n' + traceback.format_exc())
                    self.speak_dialog('error.removing.item', {'item': item, 'list': self.listName})
            else:
                lists = self.get_lists()
                if lists == []:
                    self.speak_dialog('could.not.find.any.list')
                    return
                
                for list in lists:
                    if list.get('name').lower() == listName.lower():
                        try:
                            self.bring.removeItem(list.get('listUuid'), item)
                            self.speak_dialog('item.was.removed', {'item': item, 'list': list.get('name')})
                            return
                        except:
                            self.log.exception(f'Could not remove item from list {listName}:\n' + traceback.format_exc())
                            self.speak_dialog('error.removing.item', {'item': item, 'list': listName})
                            return
                        

                self.speak_dialog('list.not.recognized', {'input': listName})

        else:
            self.speak_dialog('not.logged.in')


    @intent_handler('change.active.list.intent')
    def change_active_list(self, message):
        """
        Changes the active list in local settings.
        If name is explicitly spoken, will try to match to fetched lists.
        Else will present all list names and let user choose.
        """
        newList = message.data.get('new_list')
        lists = self.get_lists()
        if lists == []:
            self.speak_dialog('could.not.find.any.list')
            return False

        if newList == None:
            names = []
            for list in lists:
                names.append(list.get('name'))

            self.speak_dialog('choose.list')
            selection = self.ask_selection(names, numeric=True)
            if selection == None:
                return False

            for list in lists:
                if selection.lower() == list.get('name').lower():
                    self.settings['active_list'] = selection
                    self.listUuid = list.get('listUuid')
                    self.listName = list.get('name')
                    self.speak_dialog('active.list.set.to', {'list_name': self.listName})
                    return True
        else:
            for list in lists:
                if newList.lower() == list.get('name').lower():
                    self.settings['active_list'] = newList
                    self.listUuid = list.get('listUuid')
                    self.listName = list.get('name')
                    self.speak_dialog('active.list.set.to', {'list_name': self.listName})
                    return True
            self.speak_dialog('list.not.recognized', {'input': newList})
            return False

    @intent_handler('what.is.active.list.intent')
    def what_is_active_list(self):
        if self.fetch_active_list():
            self.speak_dialog('active.list.is', {'list_name': self.listName})
            return
        self.speak_dialog('could.not.find.active.list')



def create_skill():
    return BringShoppingLists()