import os
import ast
import csv
from sys import maxsize
csv.field_size_limit(maxsize)

'''Schreib Operationen'''
def write_iterable_to_file(path, data):
    with open(path, 'w') as f:
        for tupl in data:
            f.write(str(tupl) + '\n')

def append_to_file(path, data):
    with open(path, 'a') as f:
        f.write(data + '\n')

def append_row_to_csv(path, row):
    with open (path, 'a') as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(row)


'''Lese Operationen'''
def file_to_set(file_name):
    out = set()
    with open(file_name, 'rt') as f:
        try: # If a line in the file seems to be a tuple: Create set of tuples
            for line in f:
                line.replace('\n', '')
                out.add(ast.literal_eval(line))
        except SyntaxError: #Else: create set of strings
            for line in f:
                out.add(line.replace('\n', ''))
    return out

def csv_to_list(file_name):
    out = []
    with open(file_name, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            out.append(row)
    return out

def length_of_csv(file):
    with open(file) as f:
        return len(list(csv.reader(f)))
