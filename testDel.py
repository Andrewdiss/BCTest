from hashlib import sha256
from uuid import uuid4


x = 5
y = 0

while sha256(str(y * x).encode()).hexdigest()[-1] != '5':
    y += 1
print("The solution is y = {}".format(y))

print 5*21

print sha256('105').hexdigest()
# name = "Fred"
# age = 42

uniquie = str(uuid4()).replace('-', '')
print len(uniquie)
print uniquie
# print f'He said his name is {name} and he is {age} years old'