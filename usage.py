import dash
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc

from dash_network import Network

import pandas as pd
from pandas import ExcelFile
from azure.storage.blob import BlockBlobService
import json

app = dash.Dash(__name__)

app.scripts.config.serve_locally = True
app.css.config.serve_locally = True

alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
nums = '12345678'

selected_colors = ['#006', '#060', '#600', '#A80', '#A08']

def net_data(selected):
    selected_letter = selected and selected[0]

    def make_link(i, j, ids=alphabet):
        return {'source': ids[i], 'target': ids[j]}

    def not_selected(i, j):
        return selected_letter != alphabet[i] and selected_letter != alphabet[j]

    nodes_df = pd.read_excel('ontology.xlsx', sheet_name='node')
   # nodes_new = [{'id':item} for item in nodes_df.Entity.tolist()]

    nodes_new = [{'id': row['Entity'], 'radius': row['Weight']} for index, row in nodes_df.iterrows()]
    print(nodes_new)
    nodes = [{'id': letter} for letter in alphabet if letter != selected_letter]
    print(nodes)

    links_df = pd.read_excel('ontology.xlsx', sheet_name='link')
    links_new = [{'source':row['node_in'], 'target':row['node_out']} for index, row in links_df.iterrows()]
    print(links_new)
    links = ([make_link(i, i - 1) for i in range(26) if not_selected(i, i - 1)] +
             [make_link(i, i - 2) for i in range(26) if not_selected(i, i - 2)])
    print(links)

    def add_select(prefix, suffix, external_links):
        suffix0 = suffix and suffix[0]
        new_ids = [prefix + i for i in nums]
        color = selected_colors[(len(prefix) - 1) % len(selected_colors)]
        nodes.extend([{'id': new_id, 'color': color} for new_id in new_ids])
        links.extend([make_link(i, i - 1, new_ids) for i in range(7)])
        links.extend([make_link(i, i - 2, new_ids) for i in range(7)])
        links.append({'source': new_ids[0], 'target': external_links[0]})
        links.append({'source': new_ids[1], 'target': external_links[1]})
        links.append({'source': new_ids[4], 'target': external_links[2]})
        if len(external_links) > 3:
            links.append({'source': new_ids[5], 'target': external_links[3]})
        if suffix:
            s0num = nums.index(suffix0)
            new_external = [new_ids[s0num - 1], new_ids[s0num], new_ids[(s0num + 1) % 8]]
            add_select(prefix + suffix0, suffix[1:], new_external)

    if selected:
        i = alphabet.index(selected_letter)
        neighbors = [alphabet[i - 2], alphabet[i - 1], alphabet[(i + 1) % 26], alphabet[(i + 2) % 26]]
        add_select(selected_letter, selected[1:], neighbors)

    return {
        'nodes': nodes_new,
        'links': links_new
    }


def query_data(selected):

    links_df = pd.read_excel('ontology.xlsx', sheet_name='link')
    links_df = links_df[links_df['node_in'].isin(selected)]
    links_new = [{'source':row['node_in'], 'target':row['node_out']} for index, row in links_df.iterrows()]
    print(links_new)

    cur_nodes_list = links_df.node_out.unique().tolist()
    print(cur_nodes_list)
    print(type(cur_nodes_list))
    print(selected)
    print(type(selected))
    cur_nodes_list.extend(selected)
    print(cur_nodes_list)
    print(type(cur_nodes_list))

    nodes_df = pd.read_excel('ontology.xlsx', sheet_name='node')
    # nodes_new = [{'id':item} for item in nodes_df.Entity.tolist()]
    nodes_df = nodes_df[nodes_df['Entity'].isin(cur_nodes_list)]

    nodes_new = [{'id': row['Entity'], 'radius': row['Weight']} for index, row in nodes_df.iterrows()]
    print(nodes_new)

    return {
        'nodes': nodes_new,
        'links': links_new
    }

app.layout = html.Div([
    html.H2('Click a node to expand it, or the background to return'),
    Network(
        id='net',
        data=net_data(''),
        width = 700,
        height = 500,
        nodeRadius= 20
    ),
    html.Div(id='output'),
    dcc.Interval(
        id= 'interval-component',
        interval = 5*1000,
        n_intervals=0
    )
])


#@app.callback(Output('net', 'data'),
#              [Input('net', 'selectedId')])
#def update_data(selected_id):
#    return net_data(selected_id)

@app.callback(Output('net', 'data'),
              [Input('interval-component', 'n_intervals')])
def update_data(n):
    print("watch dog...")
    if n > 1:
        print("start condtion")
        block_blob_service = BlockBlobService(account_name='cldemo2rocblobstorage',
                                              account_key='DLY7/3KYBmGGE8YvBXL9gAsnx7LuFN901TA0XNeHBoLoWBi6xT+oEkNmOmitRCsBqrCo9CDmKdfjChfE5PklHg==')
        #containers = block_blob_service.list_containers()
        #for c in containers:
        #    print(c.name)
        blob = block_blob_service.get_blob_to_text('ontology-blob-container', 'file1.json')
        #jsonObj = json.loads(blob.content.split('\n'))
        jsonObj = json.loads(blob.content)
        print(jsonObj['ActivityList'])
        return query_data(jsonObj['ActivityList'])
    else:
        print("init...")
        return(net_data(''))

@app.callback(Output('output', 'children'),
              [Input('net', 'selectedId'), Input('net', 'data')])
def list_connections(selected_id, data):
    return 'You selected node "{}" on a graph with {} nodes and {} links'.format(
        selected_id, len(data['nodes']), len(data['links']))

app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'
})

if __name__ == '__main__':
    app.run_server(debug=True)
