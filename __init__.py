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

    def update_active_list(self):
        """
        Tries to set the active list to the one saved in settings.
        Returns True if uuid and name could be set.
        Returns False otherwise.
        """
        activeListName = self.settings.get('active_list').lower()
        lists = self.get_lists()

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
        


    # def get_list(self):
    #     """"
    #     Tries to return listUuid of set default list.
    #     Returns listUuid of first found list otherwise.

    #     Sets list name as a side effect.
    #     """
    #     if self.listUuid != '':
    #         return self.listUuid
        
    #     if self.validate_login():
    #         try:
    #             lists = self.bring.loadLists()['lists']
    #         except:
    #             self.log.exception('Failed to fetch lists: ' + traceback.format_exc())
    #             raise

    #         if self.settings.get('default_list', '') != '':
    #             for list in lists:
    #                 if list['name'] == self.settings.get('default_list', ''):
    #                     self.listUuid = list['listUuid']
    #                     self.listName = list['name']
    #                     return self.listUuid
            
    #         self.log.debug('Chosen default shopping list name not recognized, choosing first list.')
    #         self.listUuid = lists[0]['listUuid']
    #         self.listName = lists[0]['name']
    #         return self.listUuid


    @intent_handler('add.to.active.shopping.list.intent')
    def add_to_active_shopping_list(self, message):
        if self.validate_login():
            item = message.data.get('item').capitalize()

            try:
                if not self.update_active_list(): 
                    self.speak_dialog('could.not.find.any.list')
                    return
                self.bring.saveItem(self.listUuid, item)
                self.speak_dialog('item.was.added', {'item': item, 'list': self.listName})
            except:
                self.log.exception('Error: Could not add item to list:\n' + traceback.format_exc())
                self.speak_dialog('error.adding.item', {'item': item, 'list': self.listName})
        else:
            self.speak_dialog('not.logged.in')


    @intent_handler('remove.from.active.shopping.list.intent')
    def remove_from_active_shopping_list(self, message):
        if self.validate_login():
            item = message.data.get('item').capitalize()

            try:
                if not self.update_active_list(): 
                    self.speak_dialog('could.not.find.any.list')
                    return
                self.bring.removeItem(self.listUuid, item)
                self.speak_dialog('item.was.removed', {'item': item, 'list': self.listName})
            except:
                self.log.exception('Error: Could not remove item from list:\n' + traceback.format_exc())
                self.speak_dialog('error.removing.item', {'item': item, 'list': self.listName})
        else:
            self.speak_dialog('not.logged.in')




def create_skill():
    return BringShoppingLists()