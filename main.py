import requests
from tqdm import tqdm
import datetime
import json

vk_token = ''
ya_token = ''


def write_to_file_json(file_name: str, data):
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_photos(id_list: list):
    users_photos_list = []

    for user_id in id_list:
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
                'album_id': 'profile',
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
            photos_list.append({'title': photo_title, 'size': photo_size, 'url': photo_url})

        users_photos_list.append({'user_name': user_name, 'photos': photos_list})

    write_to_file_json('photos_data.json', users_photos_list)
    return users_photos_list


def add_album(yandex_token, album_path):
    requests.put(
        'https://cloud-api.yandex.net/v1/disk/resources',
        headers={'Authorization': f'OAuth {yandex_token}'},
        params={'path': f'disk:/{album_path}'}
    )


def upload_photos_to_yandex(yandex_token, album_path: str):
    add_album(yandex_token, album_path)
    users_photos = get_photos(ids_list)

    for user in users_photos:
        add_album(yandex_token, f"{album_path}/{user['user_name']}")
        for photo in tqdm(user['photos']):
            requests.post(
                'https://cloud-api.yandex.net/v1/disk/resources/upload',
                headers={'Authorization': f'OAuth {yandex_token}'},
                params={'path': f"disk:/{album_path}/{user['user_name']}/{photo['title']}.jpg", 'url': photo['url']}
            )


ids_list = []

upload_photos_to_yandex(ya_token, 'profile_photos')
