import os
from datetime import datetime

from DB.db_tables import create_commands, delete_commands
import psycopg2
from configparser import ConfigParser
import sqlalchemy
from VK.Search_data import status_dict, sex_dict


class DB():

    def __init__(self, dir_path='\\DB'):
        self.dir_path = dir_path
        db_settings = self.__get_db_settings__()
        self.connection = None
        self.sa_connection = None
        self._get_db_connection(db_settings)
        self.db_name = db_settings.get('db_name')
        self.db_user = db_settings.get('user')
        self.db_password = db_settings.get('password')
        self.db_port = db_settings.get('port')
        self._get_sa_connection()

    def _get_sa_connection(self):
        engine = sqlalchemy.create_engine(f'postgresql+psycopg2://{self.db_user}:{self.db_password}@localhost:{self.db_port}/{self.db_name}')
        self.sa_connection = engine.connect()


    def __get_db_settings__(self):
        config = ConfigParser()
        config.read(os.getcwd() + self.dir_path + '\\db_settings.ini')
        return {
        'db_name' : config.get('DB', 'db_name'),
        'user' : config.get('DB', 'user'),
        'password' : config.get('DB', 'password'),
        'port' : config.getint('DB', 'port')
        }

    def _get_db_connection(self, db_settings):
        try:
            self.connection = psycopg2.connect(
            database=db_settings['db_name'],
            user=db_settings['user'],
            password=db_settings['password'],
            port=db_settings['port']
            )
        except psycopg2.OperationalError as e:
            #inf = sys.exc_info()
            print(f"Ошибка подключения '{e}'")
        return self.connection

    def execute_query(self, query):
        self.connection.autocommit = True
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
        except psycopg2.OperationalError as e:
            print(e)


    def create_tables(self):
        for query in create_commands:
            self.execute_query(query=query)

    def user_exist(self, user_id, table_name):
        return self.sa_connection.execute(f'''SELECT id FROM {table_name} WHERE id = {user_id}''').fetchone()

    def _delete_tables(self):
        for query in delete_commands:
            self.execute_query(query=query)

    def add_client(self, vk_id, c_name, c_surname, c_sex):

        self.sa_connection.execute(f'''INSERT INTO Clients(id, c_name, c_surname, c_sex, c_upd) 
                                        VALUES('{vk_id}', '{c_name}','{c_surname}', {c_sex},'{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}')''')

    def save_search(self, user_id, column_name, column_value):
        # cl_id = self.client_id_by_vk_id(user_id)
        founded_line = self.sa_connection.execute(f'''SELECT * FROM searches WHERE client_id = {user_id}''').fetchone()
        if founded_line:
            if type(column_value) == str:
                column_value = f"'{column_value}'"
            self.sa_connection.execute(f'''UPDATE searches SET {column_name} = {column_value}, upd = '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}' WHERE client_id = {user_id}''')
        else:
            self.sa_connection.execute(f'''INSERT INTO Searches(client_id, {column_name}, upd)
                                        VALUES({user_id}, {column_value}, '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}')''')

    def delete_search_params(self, user_id):
        self.sa_connection.execute(f'''DELETE FROM Searches WHERE client_id = {user_id}''')

    def clear_table_clients_users(self, cl_id):
        self.sa_connection.execute(f'''DELETE FROM Search_Users WHERE search_id IN (SELECT id FROM Searches WHERE client_id = {cl_id} LIMIT 1)''')


    def get_current_search_params(self, user_id):
        search_params = self.sa_connection.execute(f'''SELECT city, status_id, sex, min_age, max_age FROM searches WHERE client_id = {user_id}''').fetchone()
        if search_params:
            if search_params != None:
                current_search_status = status_dict.get(str(search_params[1]))
                current_search_sex = sex_dict.get(str(search_params[2]))
            else:
                current_search_status = ''
                current_search_sex = ''


            search_str = f'''       Город: {search_params[0]}\n         Статус: {current_search_status}\n        Пол: {current_search_sex}\n        от {search_params[3]}\n         до {search_params[4]}'''
        else:
            search_str = f'''       Город: \n       Статус: \n      Пол: \n         от: \n         до: '''
        return f'   Параметры поиска:\n     {search_str.replace("None", "")}'

    def get_dict_of_search_params(self, user_id):
        search_params = self.sa_connection.execute(
            f'''SELECT city, city_id, status_id, sex, min_age, max_age, upd, id FROM searches WHERE client_id = {user_id}''').fetchone()
        if search_params == None:
            return None
        else:

            return {'city':search_params[0], 'city_id':search_params[1],
                'status_id':search_params[2], 'sex':search_params[3],
                'min_age':search_params[4], 'max_age':search_params[5], 'upd': search_params[6], 'id': search_params[7]}

    def find_users(self, user_id):
        '''Поиск в БД'''
        search_res = self.sa_connection.execute(f'''SELECT u_id, u_name, u_surname, u_age FROM Search_users
                                                    JOIN Users ON Users.id = Search_users.u_id 
                                                    WHERE Search_users.u_id != {user_id}
                                                    AND Search_users.u_id NOT IN (
                                SELECT user_id FROM Clients_Users
                                WHERE Clients_Users.client_id = {user_id}) LIMIT 1''').fetchone()
        return search_res


    def add_users_into_Users(self, user_id, search_list):
        record_list = [ (i["vk_id"], i["u_name"], i["u_surname"], i["u_status"], i["u_age"], i["u_sex"]) for i in search_list]
        cursor = self.connection.cursor()
        insert_query = f'''INSERT INTO USERS(id, u_name, u_surname, u_status, u_age, u_sex, u_upd) VALUES (%s,%s,%s,%s,%s,%s,'{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}') 
                            ON CONFLICT(id) DO NOTHING'''
        result = cursor.executemany(insert_query, record_list)
        self.connection.commit()
        print('test')

    def add_into_Search_Users(self, user_id, search_list):

        search_id = self.sa_connection.execute(f'''SELECT id FROM Searches WHERE client_id = {user_id} LIMIT 1''').fetchone()[0]

        record_list = [(i["vk_id"], search_id) for i in search_list]

        self.clear_table_search_users(search_id)
        cursor = self.connection.cursor()
        insert_query = f'''INSERT INTO Search_Users(u_id, search_id) VALUES (%s,%s)'''
        result = cursor.executemany(insert_query, record_list)
        self.connection.commit()

    def delete_photos_from_bd(self, user_id):
        self.sa_connection.execute(f'''DELETE FROM User_Photos WHERE user_id = {user_id}''')

    def add_photos_to_bd(self, user_id, user_photos):


        record_list = [(user_id, i) for i in user_photos]

        cursor = self.connection.cursor()
        insert_query = f'''INSERT INTO User_Photos(user_id, photo_id) VALUES (%s,%s)'''
        result = cursor.executemany(insert_query, record_list)
        self.connection.commit()


    def clear_table_search_users(self, search_id):

        self.sa_connection.execute(f'''DELETE FROM Search_Users WHERE search_id = {search_id}''')

    def add_user_to_base(self, user_data):

        user_exists = self.user_exist(user_data['vk_id'], 'Users')

        if user_exists == None:
            self.sa_connection.execute(f'''INSERT INTO Users(vk_id, u_name, u_surname, u_age, u_birthyear, u_sex, u_upd)
                        VALUES({user_data['vk_id']}, '{user_data['u_name']}', '{user_data['u_surname']}',
                        {user_data['u_age']}, {user_data['u_birthyear']}, {user_data['u_sex']}, 
                        '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}')''')
        else:
            self.sa_connection.execute(f'''UPDATE Users SET vk_id = {user_data['vk_id']}, 
                                        u_name = {user_data['u_name']},
                                        u_surname = {user_data['u_surname']},
                                        u_age = {user_data['u_age']},
                                        u_birthyear = {user_data['u_birthyear']},
                                        u_sex = {user_data['u_sex']},
                                        upd = '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}')''')

    def add_to_photos(self, user_id, photo_list):
        for ph_id in photo_list:
            photo_exist = self.sa_connection.execute(f'''SELECT id FROM Photos WHERE photo_id = '{ph_id}' ''').fetchone()
            if not photo_exist:
                user_db_id = self.sa_connection.execute(f'''SELECT id FROM Users WHERE vk_id = {user_id}''').fetchone()[0]
                self.sa_connection.execute(f'''INSERT INTO Photos(likes_count, photo_id, user_id, upd) 
                        VALUES(0, '{ph_id}', {user_db_id}, '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}') ''')

    def get_client_db_id(self, client_id):
        res = self.sa_connection.execute(f'''SELECT id FROM Clients WHERE vk_id = {client_id}''').fetchone()
        if res != None:
            return res[0]
        else:
            return None

    def get_user_db_id(self, user_id):
        res = self.sa_connection.execute(f'''SELECT id FROM Users WHERE vk_id = {user_id}''').fetchone()
        if res != None:
            return res[0]
        else:
            return None

    def add_update_to_clients_users(self, client_id, user_id, u_liked=False, u_banned=False):
        str_exist = self.sa_connection.execute(f'''SELECT Clients_Users.id FROM Clients_Users 
                                                    JOIN Clients ON Clients.id = Clients_Users.client_id 
                                                    WHERE client_id = {client_id} AND
                                                    user_id = {user_id}''').fetchone()
        if str_exist == None:

            self.sa_connection.execute(f'''INSERT INTO Clients_Users(client_id, user_id, liked, banned, upd)
                VALUES({client_id}, {user_id}, '{u_liked}', '{u_banned}', '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}' )''')
        else:
            self.sa_connection.execute(f'''UPDATE Clients_Users SET client_id = {client_id},
                user_id = {user_id}, liked = '{u_liked}', banned = '{u_banned}',
                upd = '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}' WHERE client_id = {client_id}
                AND user_id = {user_id}''')

    def get_last_showed_user(self, client_id):
        res = self.sa_connection.execute(f'''SELECT user_id FROM Clients_Users WHERE client_id = 2061397
                                        ORDER BY upd DESC 
                                        LIMIT 1''').fetchone()
        return res

    def add_to_ignore_in_db(self, client_id, last_showed_user):
        self.sa_connection.execute(f'''UPDATE Clients_Users SET client_id = {client_id},
                        user_id = {last_showed_user}, banned = '{True}',
                        upd = '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}' WHERE client_id = {client_id}
                        AND user_id = {last_showed_user}''')

    def add_to_favourites_in_db(self, client_id, last_showed_user):
        self.sa_connection.execute(f'''UPDATE Clients_Users SET client_id = {client_id},
                        user_id = {last_showed_user}, liked = '{True}',
                        upd = '{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}' WHERE client_id = {client_id}
                        AND user_id = {last_showed_user}''')

    def get_banned_users(self, client_id):
        res = self.sa_connection.execute(f'''SELECT cu.user_id, us.u_name, us.u_surname, us.u_age FROM Clients_users cu
                                                LEFT JOIN Users us ON us.id = cu.user_id
                                                WHERE cu.client_id = {client_id} AND cu.banned = {True}''').fetchall()
        return res

    def get_favourite_users(self, client_id):
        res = self.sa_connection.execute(f'''SELECT cu.user_id, us.u_name, us.u_surname, us.u_age FROM Clients_users cu
                                                LEFT JOIN Users us ON us.id = cu.user_id
                                                WHERE cu.client_id = {client_id} AND cu.liked = {True}''').fetchall()
        return res

    def user_have_search_params(self, user_id):
        search_params = self.sa_connection.execute(f'''SELECT id, city_id, status_id, sex, min_age, max_age, upd FROM Searches s 
                                        LEFT JOIN Clients on s.id = Clients.id
                                        WHERE Clients.id = {user_id}''').fetch_one()
        if search_params == None:
            return False, None
        else:
            return True, search_params

if __name__=='__main__':
    print('test')
