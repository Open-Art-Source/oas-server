import httpx

image0 = open('/home/cecil/stanford/cs231n/project/fake-paintings/etsy/anchor/0/39.jpg', 'rb')
image1 = open('/home/cecil/stanford/cs231n/project/fake-paintings/etsy/negative/0/39.jpg', 'rb')

files = {'image-0': image0, 'image-1': image1}

res = httpx.post("http://127.0.0.1:8080/predictions/image_dissimilarity", files=files)
print(res.json())