import os
import threading
import random
import requests
import pathlib


class HTTPTest:
    def __init__(self, port = 12000):
        self.port = 12000
        self.url = f'http://localhost:{self.port}'

    
    def post_test(self, uri = '/form.html', data = None):
        print('POST Response - ')
        print("\nUrl-encoded")
        try:
            post_resp = requests.post(self.url + uri, data = data)
        except:
            print('Check your Server Connection')
            return
        print("\nStatus: ")
        print(post_resp.status_code, post_resp.reason)
        print("\nResponse Headers: ")
        for key in post_resp.headers.keys():
            print(f"{key}: {post_resp.headers[key]}")
        print("\nPage Data: ")
        print(post_resp.text)

        print("\nMultipart POST")
        files = {'file': open('post_multipart.py', 'rb')}
        try:    
            post_multi_resp = requests.post(self.url + '/form2.html', data = data, files = files)
        except:
            print('Check your Server Connection')
            return
        print("\nStatus: ")
        print(post_multi_resp.status_code, post_multi_resp.reason)
        print("\nResponse Headers: ")
        for key in post_multi_resp.headers.keys():
            print(f"{key}: {post_multi_resp.headers[key]}")
        print("\nPage Data: ")
        print(post_multi_resp.text)

    

   

    def delete_test(self):
        print('DELETE Response - ')
        if os.path.exists('static/delete_sample.txt') == False:
            open("static/delete_sample.txt", 'x') #creating file if not present
        try:
            dlt_resp = requests.delete(self.url + '/delete_sample.txt')
        except:
            print('Check your Server Connection')
            return
        if dlt_resp:
            print("\nStatus: ")
            print(dlt_resp.status_code, dlt_resp.reason)
            print("\nResponse Headers: ")
            for key in dlt_resp.headers.keys():
                print(f"{key}: {dlt_resp.headers[key]}")
            print("\nContent:")
            print(dlt_resp.text)
    def get_test(self, uri = '/index.html'):
        #uri has to be in abs_path format
        print('GET Response - ')
        try:
            get_resp = requests.get(self.url + uri)
        except:
            print('Check your Server Connection')
            return
        if get_resp:
            print("Status: ")
            print(get_resp.status_code, get_resp.reason)
            print("\nResponse Headers: ")
            for key in get_resp.headers.keys():
                print(f"{key}: {get_resp.headers[key]}")
            print("\nPage Data:")
            print(get_resp.text)
        else:
            print("Response was not received")

        print('If-Modified-Since')
        try:
            get_resp_2 = requests.get(self.url + uri, headers={'If-Modified-Since': 'Sat, 29 Oct 2019 19:43:31 GMT'})
        except:
            print('Check your Server Connection')
            return
        if get_resp_2:
            print("Status: ")
            print(get_resp_2.status_code, get_resp_2.reason)
            print("\nResponse Headers: ")
            for key in get_resp_2.headers.keys():
                print(f"{key}: {get_resp_2.headers[key]}")
            print("\nPage Data:")
            print(get_resp_2.text)
        else:
            print("Response was not received")
        
        print('If-Unmodified-Since')
        try:
            get_resp_3 = requests.get(self.url + uri, headers={'If-Unmodified-Since': 'Sat, 29 Oct 2021 19:43:31 GMT'})
        except:
            print('Check your Server Connection')
            return
        if get_resp_3:
            print("Status: ")
            print(get_resp_3.status_code, get_resp.reason)
            print("\nResponse Headers: ")
            for key in get_resp_3.headers.keys():
                print(f"{key}: {get_resp_3.headers[key]}")
            print("\nPage Data:")
            print(get_resp_3.text)
        else:
            print("Response was not received")
    def head_test(self, uri = '/hello.html'):
        print('HEAD Response - ')
        try:
            head_resp = requests.head(self.url + uri)
        except:
            print('Check your Server Connection')
            return
        if head_resp:
            print("\nStatus: ")
            print(head_resp.status_code, head_resp.reason)
            print("\nResponse Headers: ")
            for key in head_resp.headers.keys():
                print(f"{key}: {head_resp.headers[key]}")
            print("\nPage Content: ")
            print(head_resp.text)
    def put_test(self):
        print('PUT Response - ')
        # file = {'put_sample.txt': open('put_sample.txt', 'rb')}
        try:
            put_resp = requests.put(self.url + '/put_res.txt')
        except:
            print('Check your Server Connection')
            return
        if put_resp:
            print("\nStatus: ")
            print(put_resp.status_code)
            print("\nResponse Headers: ")
            for key in put_resp.headers.keys():
                print(f"{key}: {put_resp.headers[key]}")
        else:
            print('Err')

if __name__ == "__main__":
    test = HTTPTest()
    print("GET Test: \n")
    test.get_test()
    print("===============")
    print("POST Test: \n")
    test.post_test(data = {'fname': 'first_name', 'lname': 'last_name'})
    print("===============")
    print("HEAD Test: \n")
    test.head_test()
    print("===============")
    print("PUT Test: \n")
    test.put_test()
    print("===============")
    print("===============")
    print("DELETE Test: \n")
    test.delete_test()




