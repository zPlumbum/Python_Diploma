import requests
from tqdm import tqdm
import datetime
import json

vk_token = ''
ya_token = ''
inst_token = ''


def write_to_file_json(file_name: str, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_photos_vk(ids_list_vk: list, album_id):
    users_photos_list = []

    for user_id in ids_list_vk:
        response_id = requests.get(
            'https://api.vk.com/method/users.get',
            params={
                'access_token': vk_token,
                'user_ids': user_id,
                'v': 5.122
            }
        )
        user_name = f"{response_id.json()['response'][0]['first_name']} {response_id.json()['response'][0]['last_name']}"

        response_photos = requests.get(
            'https://api.vk.com/method/photos.get',
            params={
                'access_token': vk_token,
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


def get_photos_inst(ids_list_inst: list, max_count=10):
    users_photos_list = []
    count = 0

    for user_id in ids_list_inst:
        response_username = requests.get(
            f'https://graph.instagram.com/{user_id}',
            params={
                'fields': 'username',
                'access_token': inst_token
            }
        )
        user_name = response_username.json()['username']

        response_photos = requests.get(
            f'https://graph.instagram.com/{user_id}/media',
            params={
                'fields': 'username,media_type,media_url,timestamp,children{media_type,media_url,timestamp}',
                'access_token': inst_token
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


def upload_photos_to_yandex(yandex_token, ids_list_vk, album_id, album_path_vk: str, ids_list_inst=None, album_path_inst=None):
    print('Идет загрузка фотографий из Вконтакте:')
    add_album(yandex_token, album_path_vk)
    users_photos_vk = get_photos_vk(ids_list_vk, album_id)

    for user_vk in users_photos_vk:
        add_album(yandex_token, f"{album_path_vk}/{user_vk['user_name']}")
        for photo in tqdm(user_vk['photos']):
            requests.post(
                'https://cloud-api.yandex.net/v1/disk/resources/upload',
                headers={'Authorization': f'OAuth {yandex_token}'},
                params={'path': f"disk:/{album_path_vk}/{user_vk['user_name']}/{photo['title']}.jpg",
                        'url': photo['url']}
            )

    if (ids_list_inst is not None) and (album_path_inst is not None):
        print('\nИдет загрузка постов из инстаграма:')
        users_photos_inst = get_photos_inst(ids_list_inst)
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
    print('\nЗагрузка завершена!')


user_ids_vk = []
user_ids_inst = []

upload_photos_to_yandex(ya_token, user_ids_vk, 'profile', 'profile_photos_vk', user_ids_inst, 'instagram')
