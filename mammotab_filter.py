# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# +
# # +
from email import header
import numpy as np
from tqdm import tqdm

import gzip, json

import sys
import os

import numpy as np
import sys

# -

source_folder = sys.argv[1]
folder_name = sys.argv[2]
output_folder_name = sys.argv[3]

min_links_number = 3 # minimum number of links in a single column for a table to be in the dataset

all_diz = []

kept = 0
total = 0

def clean_links(link):
    if '#' in link:
        # remove links that refer to a page section
        return ''
    else:
        return link
    
clean_links_v = np.vectorize(clean_links)

for f_name in tqdm(os.listdir(os.path.join(source_folder, folder_name))):
    #print(f_name)
    if 'diz_' in f_name:
        with gzip.open(os.path.join(source_folder, folder_name, f_name), 'rt') as f:
            diz = json.load(f)

    tables_to_keep = set()

    for tabcode, tab in diz['tables'].items():
        text_mat = np.array(tab['text'])
        #text_mat = clean_cell_v(text_mat) # TODO TOGLIERE
        header_mat = np.array(tab['header'])
        link_mat = np.array(tab['link'])
        cells_mat = np.array(tab['cells'])

        # by col
        col_to_remove = set()
        for col_id, col in enumerate(text_mat.T):
            if 'IMAGE' in col \
                or 'HELP_PAGE' in col \
                    or 'WIKI_PROJ_PAGE' in col:
                col_to_remove.add(col_id)
            else:
                # all empty string or -
                if all(map(lambda x: x in set(['', ' ', "-"]), col[len(header_mat):])):
                    col_to_remove.add(col_id)
                # all none
                elif all(map(lambda x: 'none' in x.lower(), col[len(header_mat):])):
                    col_to_remove.add(col_id)
                # all wikidata Q ids
                elif all(map(lambda x: x.startswith('Q') and x[1:].isnumeric(), col[len(header_mat):])):
                    col_to_remove.add(col_id)

        col_to_keep = set(range(text_mat.shape[1])) - col_to_remove
        col_to_keep = list(col_to_keep)

        text_mat = text_mat[:,col_to_keep]
        if header_mat.size > 0:
            header_mat = header_mat[:,col_to_keep]
        link_mat = link_mat[:,col_to_keep]
        cell_col_to_keep = list(map(lambda x: x*2, col_to_keep)) + list(map(lambda x: x*2+1, col_to_keep))
        cells_mat = cells_mat[:,cell_col_to_keep]

        # by row
        row_to_remove = set()
        for row_id, row in enumerate(text_mat):
            if all(map(lambda x: x in set(['', ' ', "-"]), row)):
                row_to_remove.add(row_id)
            elif all(map(lambda x: 'none' in x.lower(), row)):
                row_to_remove.add(row_id)

        row_to_keep = set(range(text_mat.shape[0])) - row_to_remove
        header_row_to_keep = list(row_to_keep.intersection(set(range(header_mat.shape[0]))))
        row_to_keep = list(row_to_keep)

        text_mat = text_mat[row_to_keep]
        if header_mat.size > 0:
            header_mat = header_mat[header_row_to_keep]
        link_mat = link_mat[row_to_keep]
        cells_mat = cells_mat[row_to_keep]

        # clean links
        if link_mat.size > 0:
            link_mat = clean_links_v(link_mat)


        assert text_mat.shape == link_mat.shape
        assert text_mat.shape[0] == cells_mat.shape[0]
        assert text_mat.shape[1] * 2 == cells_mat.shape[1]
        if header_mat.size > 0:
            assert text_mat.shape[1] == header_mat.shape[1]
            assert text_mat.shape[0] >= header_mat.shape[0]

        tab['text'] = text_mat.tolist()
        tab['header'] = header_mat.tolist()
        tab['link'] = link_mat.tolist()
        tab['cells'] = cells_mat.tolist()

        # if table is not empty
        if text_mat.size > 0:
            # check max number of links per column (to filter table with too few links)
            link_sum = np.array(np.sum(link_mat != '', axis = 0))          #sum of links
            assert link_sum.shape[0] == text_mat.shape[1]
            current_max = np.amax(link_sum)

            if current_max >= min_links_number:
                tables_to_keep.add(tabcode)

    total += len(diz['tables'])

    diz['tables'] = {tabcode: table for tabcode, table in diz['tables'].items() if tabcode in tables_to_keep}

    # skip pages with no tables
    if diz['tables']:
        kept += len(diz['tables'])
        os.makedirs(os.path.join(output_folder_name, folder_name), exist_ok=True)
        with gzip.open(os.path.join(output_folder_name, folder_name, f_name), 'wt') as f:
            json.dump(diz, f)

print('kept', kept, 'of', total)