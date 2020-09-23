import requests
from tqdm import tqdm
import datetime
import json

vk_token = ''
ya_token = ''
inst_token = ''

ya_headers = {'Authorization': f'OAuth {ya_token}'}
vk_version = 5.122


class YandexAPI:
    def __init__(self, album_path, users_photos, yandex_headers):
        self.album_path_vk = album_path
        self.users_photos_vk = users_photos
        self.yandex_headers = yandex_headers

    def upload_to_yandex(self, headers):
        for user_vk in self.users_photos_vk:
            add_album(f"{self.album_path_vk}/{user_vk['user_name']}", headers)
            for photo in tqdm(user_vk['photos']):
                requests.post(
                    'https://cloud-api.yandex.net/v1/disk/resources/upload',
                    headers=self.yandex_headers,
                    params={'path': f"disk:/{self.album_path_vk}/{user_vk['user_name']}/{photo['title']}.jpg",
                            'url': photo['url']}
                )
        print('Загрузка завершена!')


class VkApi:
    def __init__(self, token):
        self.token = token

    def get_username(self, user_id):
        response_id = requests.get(
            'https://api.vk.com/method/users.get',
            params={
                'access_token': self.token,
                'user_ids': user_id,
                'v': vk_version
            }
        )
        user_name = None
        if 'error' in response_id.json().keys():
            print(f'Не удалось получить информацию о пользователе с id "{user_id}".')
        else:
            user_name = f"{response_id.json()['response'][0]['first_name']} {response_id.json()['response'][0]['last_name']}"
        return user_name

    def get_photos(self, user_id, album_id):
        response_photos = requests.get(
            'https://api.vk.com/method/photos.get',
            params={
                'access_token': self.token,
                'owner_id': user_id,
                'album_id': album_id,
                'rev': 1,
                'extended': 1,
                'v': vk_version
            }
        )
        photos_list = []

        for photo in response_photos.json()['response']['items']:
            photo_url = photo['sizes'][-1]['url']
            photo_size = photo['sizes'][-1]['type']
            photo_title = str(photo['likes']['count'])
            for item in photos_list:
                if photo_title == item['title']:
                    photo_title = f'{photo_title}_{datetime.date.today()}'
                    break
            photos_list.append({'title': photo_title, 'size': photo_size, 'url': photo_url})
        return photos_list


class InstApi:
    def __init__(self, token):
        self.token = token

    def get_username(self, user_id):
        response_username = requests.get(
            f'https://graph.instagram.com/{user_id}',
            params={
                'fields': 'username',
                'access_token': self.token
            }
        )
        user_name = response_username.json()['username']
        return user_name

    def get_photos(self, user_id, count, max_count):
        response_photos = requests.get(
            f'https://graph.instagram.com/{user_id}/media',
            params={
                'fields': 'username,media_type,media_url,timestamp,children{media_type,media_url,timestamp}',
                'access_token': self.token
            }
        )
        photos_list = []

        for photo in response_photos.json()['data']:
            if count < max_count:
                count += 1

                if 'children' in photo.keys():
                    for children_photo in photo['children']['data']:
                        photo_title = children_photo['timestamp'][0:10]
                        photo_type = children_photo['media_type']
                        photo_url = children_photo['media_url']
                        photo_extension = 'jpg' if photo_type == 'IMAGE' else 'VIDEO'

                        photos_list.append({'title': photo_title,
                                            'type': photo_type,
                                            'extension': photo_extension,
                                            'url': photo_url})
                else:
                    photo_title = photo['timestamp'][0:10]
                    photo_type = photo['media_type']
                    photo_url = photo['media_url']
                    photo_extension = 'jpg' if photo_type == 'IMAGE' else 'mp4'

                    photos_list.append({'title': photo_title,
                                        'type': photo_type,
                                        'extension': photo_extension,
                                        'url': photo_url})
            else:
                break
        return photos_list


def check_dialog():
    yandex_token = ya_token
    vkontakte_token = vk_token
    while (vkontakte_token == '') or (yandex_token == ''):
        print('Пожалуйста, введите токены "Вконтакте" и "Яндекс.Диска"')
        if vkontakte_token == '':
            vkontakte_token = input('Токен "Вконтакте": ')
        if yandex_token == '':
            yandex_token = input('Токен "Яндекс.Диска": ')
        print()
    yandex_headers = {'Authorization': f'OAuth {yandex_token}'}

    socials_set = {'vk', 'instagram'}
    socials_to_upload = set(input('Введите через пробел названия социальных сетей, откуда хотите загрузить фотографии'
                                  '\n(например, vk instagram): ').split())
    while not socials_to_upload.issubset(socials_set):
        socials_to_upload = set(input('Вы ввели неверные данные. Пожалуйста, повторите попытку: ').split())

    return vkontakte_token, yandex_token, yandex_headers, socials_to_upload


def get_id_from_nickname(nickname_list, token):
    ids_list = []

    for nickname in nickname_list:
        is_exists = False

        while (is_exists is False) and (nickname != 'skip'):
            is_exists = False
            response_nick = requests.get(
                'https://api.vk.com/method/users.search',
                params={
                    'access_token': token,
                    'q': nickname,
                    'v': vk_version
                }
            )
            if len(response_nick.json()['response']['items']) > 0:
                user_id = response_nick.json()['response']['items'][0]['id']
                ids_list.append(user_id)
                is_exists = True
            else:
                nickname = input(f'Не найден id по запросу "{nickname}". Пожалуйста, повторите попытку '
                                 f'или введите "skip", чтобы пропустить этот id: ')

    return ids_list


def write_to_file_json(file_name, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_photos_vk(ids_list_vk, album_id, token=vk_token):
    users_photos_list = []
    vk_api = VkApi(token)

    for user_id in ids_list_vk:
        user_name = vk_api.get_username(user_id)
        if user_name is not None:
            photos_list = vk_api.get_photos(user_id, album_id)
            users_photos_list.append({'user_name': user_name, 'photos': photos_list})

    write_to_file_json('photos_vk.json', users_photos_list)
    return users_photos_list


def get_photos_inst(ids_list_inst, token=inst_token, max_count=10):
    users_photos_list = []
    count = 0
    inst_api = InstApi(token)

    for user_id in ids_list_inst:
        user_name = inst_api.get_username(user_id)
        photos_list = inst_api.get_photos(user_id, count, max_count)
        users_photos_list.append({'user_name': user_name, 'photos': photos_list})

    write_to_file_json('photos_inst.json', users_photos_list)
    return users_photos_list


def add_album(album_path, headers):
    requests.put(
        'https://cloud-api.yandex.net/v1/disk/resources',
        headers=headers,
        params={'path': f'disk:/{album_path}'}
    )


def upload_photos_to_yandex():
    vkontakte_token, yandex_token, yandex_headers, socials_to_upload = check_dialog()

    if 'vk' in socials_to_upload:
        print('\nЗагрузка фото из Вконтакте.')
        nickname_list_vk = input('Введите через пробел id пользователей: ').split()
        ids_list_vk = get_id_from_nickname(nickname_list_vk, vkontakte_token)
        mode = input('Для быстрой загрузки введите - "0", для выбора настроек загрузки введите - "1": ')
        album_id = ''
        album_path_vk = ''

        while mode not in ['0', '1']:
            mode = input('Вы ввели неверные данные, повторите попытку: ')
        if mode == '0':
            album_id = 'profile'
            album_path_vk = 'profile-photos-vk'
        elif mode == '1':
            album_id = input('Введите название альбома, откуда хотите загрузить фото. "profile" - фото профиля, "wall" - фото со стены: ')
            album_path_vk = input('Укажите название новой папки на Яндекс.Диске, куда будут загружаться фото: ')

        print('\nИдет загрузка фотографий из Вконтакте:')

        add_album(album_path_vk, yandex_headers)
        users_photos_vk = get_photos_vk(ids_list_vk, album_id, vkontakte_token)
        ya_uploader = YandexAPI(album_path_vk, users_photos_vk, yandex_headers)

        ya_uploader.upload_to_yandex(yandex_headers)

    if 'instagram' in socials_to_upload:
        instagram_token = inst_token
        while instagram_token == '':
            print('\nПожалуйста, введите токен "Instagram": ')
            instagram_token = input('Токен "Instagram": ')

        print('\nЗагрузка фото из Instagram.')
        ids_list_inst = input('Введите через пробел id пользователей: ').split()
        mode = input('Для быстрой загрузки введите - "0", для выбора настроек загрузки введите - "1": ')
        album_path_inst = ''

        while mode not in ['0', '1']:
            mode = input('Вы ввели неверные данные, повторите попытку: ')
        if mode == '0':
            album_path_inst = 'profile-photos-instagram'
        elif mode == '1':
            album_path_inst = input('Укажите название новой папки на Яндекс.Диске, куда будут загружаться фото: ')

        print('\nИдет загрузка постов из инстаграма:')

        users_photos_inst = get_photos_inst(ids_list_inst, instagram_token)
        add_album(album_path_inst, yandex_headers)
        ya_uploader = YandexAPI(album_path_inst, users_photos_inst, yandex_headers)

        ya_uploader.upload_to_yandex(yandex_headers)


if __name__ == '__main__':
    upload_photos_to_yandex()
