import requests
from tqdm import tqdm
import datetime
import json

vk_token = ''
ya_token = ''
inst_token = ''


def get_id_from_nickname(nickname_list, token=vk_token):
    ids_list = []

    for nickname in nickname_list:
        response_nick = requests.get(
            'https://api.vk.com/method/users.search',
            params={
                'access_token': token,
                'q': nickname,
                'v': 5.122
            }
        )
        user_id = response_nick.json()['response']['items'][0]['id']
        ids_list.append(user_id)
    return ids_list


def write_to_file_json(file_name: str, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_photos_vk(ids_list_vk: list, album_id, token=vk_token):
    users_photos_list = []

    for user_id in ids_list_vk:
        response_id = requests.get(
            'https://api.vk.com/method/users.get',
            params={
                'access_token': token,
                'user_ids': user_id,
                'v': 5.122
            }
        )
        user_name = f"{response_id.json()['response'][0]['first_name']} {response_id.json()['response'][0]['last_name']}"

        response_photos = requests.get(
            'https://api.vk.com/method/photos.get',
            params={
                'access_token': token,
                'owner_id': user_id,
                'album_id': album_id,
                'rev': 1,
                'extended': 1,
                'v': 5.122
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

        users_photos_list.append({'user_name': user_name, 'photos': photos_list})

    write_to_file_json('photos_vk.json', users_photos_list)
    return users_photos_list


def get_photos_inst(ids_list_inst: list, token=inst_token, max_count=10):
    users_photos_list = []
    count = 0

    for user_id in ids_list_inst:
        response_username = requests.get(
            f'https://graph.instagram.com/{user_id}',
            params={
                'fields': 'username',
                'access_token': token
            }
        )
        user_name = response_username.json()['username']

        response_photos = requests.get(
            f'https://graph.instagram.com/{user_id}/media',
            params={
                'fields': 'username,media_type,media_url,timestamp,children{media_type,media_url,timestamp}',
                'access_token': token
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

        users_photos_list.append({'user_name': user_name, 'photos': photos_list})
    write_to_file_json('photos_inst.json', users_photos_list)
    return users_photos_list


def add_album(yandex_token, album_path):
    requests.put(
        'https://cloud-api.yandex.net/v1/disk/resources',
        headers={'Authorization': f'OAuth {yandex_token}'},
        params={'path': f'disk:/{album_path}'}
    )


def upload_photos_to_yandex():
    yandex_token = ya_token
    vkontakte_token = vk_token
    while (vkontakte_token == '') or (yandex_token == ''):
        print('Пожалуйста, введите токены "Вконтакте" и "Яндекс.Диска"')
        if vkontakte_token == '':
            vkontakte_token = input('Токен "Вконтакте": ')
        if yandex_token == '':
            yandex_token = input('Токен "Яндекс.Диска": ')
        print()

    socials_set = {'vk', 'instagram'}
    socials_to_upload = set(input('Введите через пробел названия социальных сетей, откуда хотите загрузить фотографии'
                                  '\n(например, vk instagram): ').split())
    while not socials_to_upload.issubset(socials_set):
        socials_to_upload = set(input('Вы ввели неверные данные. Пожалуйста, повторите попытку: ').split())

    if 'vk' in socials_to_upload:
        print('\nЗагрузка фото из Вконтакте.')
        nickname_list_vk = input('Введите через пробел id пользователей: ').split()
        ids_list_vk = get_id_from_nickname(nickname_list_vk)
        mode = input('Для быстрой загрузки введите - "0", для выбора настроек загрузки введите - "1": ')

        while mode not in ['0', '1']:
            mode = input('Вы ввели неверные данные, повторите попытку: ')
        if mode == '0':
            album_id = 'profile'
            album_path_vk = 'profile-photos-vk'
        elif mode == '1':
            album_id = input('Введите название альбома, откуда хотите загрузить фото. "profile" - фото профиля, "wall" - фото со стены: ')
            album_path_vk = input('Укажите название новой папки на Яндекс.Диске, куда будут загружаться фото: ')

        print('\nИдет загрузка фотографий из Вконтакте:')

        add_album(yandex_token, album_path_vk)
        users_photos_vk = get_photos_vk(ids_list_vk, album_id, vkontakte_token)

        for user_vk in users_photos_vk:
            add_album(yandex_token, f"{album_path_vk}/{user_vk['user_name']}")
            for photo in tqdm(user_vk['photos']):
                requests.post(
                    'https://cloud-api.yandex.net/v1/disk/resources/upload',
                    headers={'Authorization': f'OAuth {yandex_token}'},
                    params={'path': f"disk:/{album_path_vk}/{user_vk['user_name']}/{photo['title']}.jpg",
                            'url': photo['url']}
                )
        print('Загрузка завершена!')

    if 'instagram' in socials_to_upload:
        instagram_token = inst_token
        while instagram_token == '':
            print('\nПожалуйста, введите токен "Instagram": ')
            instagram_token = input('Токен "Instagram": ')

        print('\nЗагрузка фото из Instagram.')
        ids_list_inst = input('Введите через пробел id пользователей: ').split()
        mode = input('Для быстрой загрузки введите - "0", для выбора настроек загрузки введите - "1": ')

        while mode not in ['0', '1']:
            mode = input('Вы ввели неверные данные, повторите попытку: ')
        if mode == '0':
            album_path_inst = 'profile-photos-instagram'
        elif mode == '1':
            album_path_inst = input('Укажите название новой папки на Яндекс.Диске, куда будут загружаться фото: ')

        print('\nИдет загрузка постов из инстаграма:')

        users_photos_inst = get_photos_inst(ids_list_inst, instagram_token)
        add_album(yandex_token, album_path_inst)

        for user_inst in users_photos_inst:
            add_album(yandex_token, f"{album_path_inst}/{user_inst['user_name']}")
            for photo in tqdm(user_inst['photos']):
                requests.post(
                    'https://cloud-api.yandex.net/v1/disk/resources/upload',
                    headers={'Authorization': f'OAuth {yandex_token}'},
                    params={'path': f"disk:/{album_path_inst}/{user_inst['user_name']}/{photo['title']}.{photo['extension']}",
                            'url': photo['url']}
                )
        print('Загрузка завершена!')


upload_photos_to_yandex()
