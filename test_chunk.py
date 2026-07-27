def chunk_list(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

keys = list(range(150))
print(list(chunk_list(keys, 100)))
