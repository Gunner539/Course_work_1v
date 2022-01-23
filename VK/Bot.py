import vk_api
import vk_api.exceptions as v_ex
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from DB.db_app import DB
from VK.Search_data import search_tasks, status_msg
from VK.VK_Client import VK_Client as vk_cl
from Common.Common_functions import prepare_photos_list_for_sending, check_days_difference


class bot_keyboards_cls():

    def __init__(self):
        self.empty_kb = VkKeyboard.get_empty_keyboard()
        self.search_menu_kb = self.get_search_menu_kb()

    def general_kb(self):


        keyboard = VkKeyboard()
        buttons_1 = ["&#128420;В игнор", "&#10145;Следующий", "&#10084;Лайк"]
        button_colors = [VkKeyboardColor.NEGATIVE, VkKeyboardColor.SECONDARY, VkKeyboardColor.POSITIVE]
        for btn, btn_color in zip(buttons_1, button_colors):
            keyboard.add_button(btn, btn_color)
        keyboard.add_line()
        keyboard.add_button('&#128269;Параметры поиска', VkKeyboardColor.PRIMARY)

        keyboard.add_line()
        buttons_3 = ["&#128545;Бан лист", "&#128525;Понравившиеся"]
        button_colors = [VkKeyboardColor.NEGATIVE, VkKeyboardColor.POSITIVE]
        for btn, btn_color in zip(buttons_3, button_colors):
            keyboard.add_button(btn, btn_color)

        return keyboard

    def get_search_menu_kb(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button("Город", VkKeyboardColor.POSITIVE)
        keyboard.add_button("Пол", VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button("Возраст", VkKeyboardColor.POSITIVE)
        keyboard.add_button("Статус", VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button('Применить настройки', VkKeyboardColor.PRIMARY)
        keyboard.add_button('Очистить настройки', VkKeyboardColor.NEGATIVE)

        return keyboard

    def back_btn(self):
        keyboard = VkKeyboard(one_time=True)
        keyboard.add_button("вернуться к настройкам", VkKeyboardColor.NEGATIVE)
        return keyboard

    def age_menu(self):
        keyboard = VkKeyboard()
        keyboard.add_button("мин. возраст", VkKeyboardColor.POSITIVE)
        keyboard.add_button("макс. возраст", VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button("&#128269;Параметры поиска")

        return keyboard

    def sex_kb(self):
        keyboard = VkKeyboard()
        keyboard.add_button("Муж.", VkKeyboardColor.POSITIVE)
        keyboard.add_button("Жен.", VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button("&#128269;Параметры поиска", VkKeyboardColor.SECONDARY)

        return keyboard

    def to_search_params(self):
        keyboard = VkKeyboard()
        keyboard.add_button("&#128269;Параметры поиска", VkKeyboardColor.SECONDARY)

        return keyboard

    def start_kb(self):
        keyboard = VkKeyboard()
        keyboard.add_button("Начать", VkKeyboardColor.PRIMARY)
        return keyboard

class VK_bot():

    def __init__(self, gr_token):
        self.gr_token = gr_token
        self.keyboards = bot_keyboards_cls()
        self.vk = vk_api.VkApi(token=self.gr_token)
        self.search_tasks = search_tasks
        self.DB = DB()
        self.user_tokens = dict()


    def get_user_info(self, user_id):
        params = {'user_ids': user_id, 'fields':'sex, relation, bdate'}
        try:
            user_vk_id = self.vk.method('users.get', params)
            return True, user_vk_id[0]
        except v_ex.ApiError as er:
            return False, er.error['error_msg']


    def get_last_message(self,user_id, offset):
        params = {'offset': offset,
                  'count' : 1,
                  'user_id': user_id,
                  'token': self.gr_token}
        last_message = self.vk.method('messages.getHistory', params)
        return last_message['items'][0]['text']

    def city_id_by_name(self, city_str):
        founded_city = self.vk.method('database.getCities', {'country_id': 1, 'q': city_str})
        if founded_city['request'].count == 1:
            return founded_city['request']['items'][0].id


    def send_empty_keyboard(self, user_id, message, keyboard):
        post = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), 'keyboard': keyboard}
        self.vk.method('messages.send', post)

    def greeting_message(self, user_id):
        keyboard = self.keyboards.general_kb()
        self.write_msg(user_id,
                       "Привет дружок. Меня зовут Саб-Зиро. Я помогу найти тебе твою любовь",
                       keyboard)
        self.write_msg(user_id,
                       '''Для того, чтобы я мог помочь тебе, мне нужен твой токен пользователя.\n
       Перейди по ссылке, скопируй текст из адресной строки браузера и отправь его ответным сообщением\n
       https://oauth.vk.com/authorize?client_id=7975991&display=page&scope=offline&response_type=token&v=5.130''')


    def do_test_user_token(self, user_id, user_token):
        testVK = vk_cl(user_token, user_id)
        try:
            test_res = testVK.vk.method('users.get', {'ids': user_id})
            return True
        except v_ex.ApiError as er:
            return False

    def start_bot(self):

        longpoll = VkLongPoll(self.vk)
        bot_keyboards = bot_keyboards_cls()

        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:

                vk_user = self.DB.user_exist(user_id=event.user_id, table_name='Clients')
                if vk_user == None:
                    user_info = self.get_user_info(user_id=event.user_id)
                    self.DB.add_client(vk_id=user_info[1]['id'],
                                       c_name= user_info[1]['first_name'],
                                       c_surname=user_info[1]['last_name'],
                                       c_sex=user_info[1]['sex'])


                if event.to_me:
                    request = event.text

                    if event.user_id not in self.user_tokens.keys():

                        last_message = self.get_last_message(event.user_id, offset=1)
                        if last_message == None:
                            self.greeting_message(event.user_id)
                            continue

                        if last_message.find('токен пользователя') != -1:
                            keyboard = bot_keyboards.general_kb()
                            self.write_msg(event.user_id, 'токен принят', keyboard)
                            parsed_token = self._parse_token_from_string(request)
                            if parsed_token == None:
                                self.write_msg(event.user_id, 'Ошибка. Некорректный токен')
                                continue
                            else:
                                if self.do_test_user_token(event.user_id, parsed_token):
                                    self.user_tokens[event.user_id] = parsed_token
                                else:
                                    self.write_msg(event.user_id, 'Ошибка. Некорректный токен')
                                    continue


                                continue
                        else:
                            self.greeting_message(event.user_id)
                            continue

                    if request.lower() == 'начать':
                        keyboard = bot_keyboards.general_kb()
                        self.write_msg(event.user_id, "поехали", keyboard)

                    elif request.lower() == '🖤в игнор':
                       last_showed_user = self.DB.get_last_showed_user(event.user_id)
                       self.DB.add_to_ignore_in_db(event.user_id, last_showed_user[0])
                       vk_finder = vk_cl(self.user_tokens[event.user_id], event.user_id)
                       vk_finder.add_to_black_list(last_showed_user[0])
                       self.show_next(event.user_id)

                    elif request.lower() == '❤лайк':
                        last_showed_user = self.DB.get_last_showed_user(event.user_id)
                        self.DB.add_to_favourites_in_db(event.user_id, last_showed_user[0])
                        vk_finder = vk_cl(self.user_tokens[event.user_id], event.user_id)
                        vk_finder.add_to_favourites(last_showed_user[0])
                        self.show_next(event.user_id)

                    elif request.lower() == '😡бан лист':
                        res = self.DB.get_banned_users(event.user_id)
                        banned_list = [f'{i+1})    http://vk.com/id{user[0]}  {user[1]} {user[2]}, {user[3]} ' for i, user in enumerate(res)]
                        self.write_msg(event.user_id, "\n".join(banned_list))

                    elif request.lower() == '😍понравившиеся':
                        res = self.DB.get_favourite_users(event.user_id)
                        fav_list = [f'{i + 1})    http://vk.com/id{user[0]} {user[1]} {user[2]}, {user[3]} ' for i, user in enumerate(res)]
                        self.write_msg(event.user_id, "\n".join(fav_list))

                    elif request.lower() == '➡следующий':
                        self.show_next(event.user_id)


                    elif request.lower() == 'вернуться':
                        keyboard = bot_keyboards.general_kb()
                        self.write_msg(event.user_id, "выберите действие", keyboard)

                    elif request.lower() == 'применить настройки':
                        keyboard = bot_keyboards.general_kb()
                        s_params = self.DB.get_dict_of_search_params(event.user_id)
                        self.DB.clear_table_search_users(s_params['id'])
                        vk_finder = vk_cl(self.user_tokens[event.user_id], event.user_id)
                        res = vk_finder.get_users_from_vk(s_params)
                        self.write_msg(event.user_id, f"Найдено {res} пользователей")
                        self.write_msg(event.user_id, "выберите действие", keyboard)



                    elif request.lower() == 'очистить настройки':
                        keyboard = bot_keyboards.search_menu_kb
                        self.DB.delete_search_params(event.user_id)
                        self.write_msg(event.user_id, "Настройки поиска очищены", keyboard)

                    elif request.lower() == 'пол':
                        keyboard = bot_keyboards.sex_kb()
                        self.write_msg(event.user_id, "Выберите пол", keyboard)

                    elif request.lower() == '🔍параметры поиска':

                        keyboard = VkKeyboard()
                        # empty_keyboard = keyboard.get_empty_keyboard()
                        # self.send_empty_keyboard(event.user_id, "", empty_keyboard)
                        keyboard = bot_keyboards.search_menu_kb
                        #self.write_msg(event.user_id, "Заполните параметры поиска", keyboard)
                        self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id), keyboard)

                    elif request.lower() == 'статус':
                        keyboard = bot_keyboards.to_search_params()
                        self.write_msg(event.user_id, status_msg, keyboard)

                    elif request.lower() == 'город':
                        keyboard = bot_keyboards.to_search_params()
                        #empty_keyboard = keyboard.get_empty_keyboard()
                        self.write_msg(event.user_id, "введите название города", keyboard)

                    elif request.lower() == 'возраст':
                        keyboard = bot_keyboards.age_menu()
                        self.write_msg(event.user_id, "выберите возраст", keyboard)


                    elif request.lower() == 'мин. возраст':
                        self.write_msg(event.user_id, "введите мин. возраст")

                    elif request.lower() == 'макс. возраст':
                        self.write_msg(event.user_id, "введите макс. возраст")

                    elif request.lower() == 'вернуться к настройкам':
                        keyboard = bot_keyboards.general_kb()
                        current_search_params = self.DB.get_current_search_params(event.user_id)
                        self.write_msg(event.user_id, current_search_params, keyboard)
                    else:
                        last_message = self.get_last_message(event.user_id, offset=1)
                        if last_message.lower() in self.search_tasks or last_message.lower().find('токен пользователя') != -1:
                           if last_message.lower() == 'введите название города':
                               VK_client = vk_cl(self.user_tokens[event.user_id], event.user_id)
                               city_id = VK_client.find_city(request.lower())

                               if city_id[0] == True:
                                   keyboard = bot_keyboards.search_menu_kb
                                   self.DB.save_search(event.user_id, 'city_id', city_id[1])
                                   self.DB.save_search(event.user_id, 'city', city_id[2])
                                   self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id), keyboard)
                               else:
                                   keyboard = bot_keyboards.back_btn()
                                   self.write_msg(event.user_id, "Ошибка ввода. Город не найден")
                                   self.write_msg(event.user_id, "Введите название города", keyboard)

                           elif last_message.find('токен пользователя') != -1:
                               keyboard = bot_keyboards.general_kb()
                               self.write_msg(event.user_id, 'токен принят', keyboard)
                               parsed_token = self._parse_token_from_string(request)
                               self.user_tokens[event.user_id] = parsed_token


                           elif last_message.lower().find('выберите пол') != -1:
                               if request.lower() in ['муж.','жен.']:
                                   keyboard = bot_keyboards.search_menu_kb
                                   self.DB.save_search(event.user_id, 'sex', 2 if request.lower() == 'муж.' else 1)
                                   self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id), keyboard)
                               else:
                                   self.write_msg(event.user_id, "Ошибка ввода")
                                   self.write_msg(event.user_id, "Выберите пол")


                           elif last_message.lower() == 'введите мин. возраст':
                               min_age = 0
                               try:
                                   min_age = int(request.lower())
                               except ValueError as ve:
                                   self.write_msg(event.user_id, "Ошибка ввода. Введите число")
                                   self.write_msg(event.user_id, "введите мин. возраст")
                               else:
                                   self.DB.save_search(event.user_id, 'min_age', min_age)
                                   self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id))
                           elif last_message.lower() == 'введите макс. возраст':
                               max_age = 0
                               try:
                                   max_age = int(request.lower())
                               except ValueError as ve:
                                   self.write_msg(event.user_id, "Ошибка ввода. Введите число")
                                   self.write_msg(event.user_id, "введите макс. возраст")
                               else:
                                   self.DB.save_search(event.user_id, 'max_age', max_age)
                                   self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id))


                        elif last_message.lower().find('выберите статус') != -1:
                               if request in ['0','1','2','3','4','5','6','7','8','9']:
                                   self.DB.save_search(event.user_id, 'status_id', int(request))
                                   self.write_msg(event.user_id, self.DB.get_current_search_params(event.user_id), bot_keyboards.search_menu_kb)
                               else:
                                   self.write_msg(event.user_id, "Ошибка ввода")
                                   keyboard = bot_keyboards.to_search_params()
                                   self.write_msg(event.user_id, status_msg, keyboard)
                        else:
                            if request.lower().find('ошибка') != -1:
                                continue

                            keyboard = bot_keyboards.general_kb()
                            self.write_msg(event.user_id, "я вас не поняла", keyboard)

    def _parse_token_from_string(self, token_string):
        str_token = ''
        try:
            str_token = token_string.split('token=')[1].split('&')[0]
            return str_token
        except IndexError as er:
            return None


    def show_next(self, client_id, black_list=None, favourites=None):

        vk_finder = vk_cl(self.user_tokens[client_id], client_id)
        if vk_finder.search_params == None:
            self.write_msg(client_id, "Ошибка. Параметры поиска не заданы")
        else:
            print('test')
            if check_days_difference(vk_finder.search_params['upd']) > 24 * 3600:
                self.DB.clear_table_clients_users(client_id)
                next_person = vk_finder.find_next()
            else:
                res = vk_finder.find_next()
                if res[0] == False:
                    self.write_msg(client_id, res[1], attachment="")
                else:
                    message_text = self.str_user_info_for_sending(res[1])
                    self.write_msg(client_id, f'''{message_text}''',
                                   attachment=prepare_photos_list_for_sending(res[1]['user_id'], res[1]['attachments']))



    def str_user_info_for_sending(self, data):
        str_to_send = f'''{data["name"]}, {data["age"]}\n{data["user_link"]}'''
        return str_to_send

    def write_msg(self, user_id, message, keyboard=None, attachment=None):
        post = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), }
        if keyboard != None:
            post["keyboard"] = keyboard.get_keyboard()
        if attachment != None:
            post["attachment"] = ",".join(attachment)
        self.vk.method('messages.send', post)
