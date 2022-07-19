"""BSD 3-Clause License

Copyright (c) 2022, Danil Napad
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."""

from bs4 import BeautifulSoup
from itertools import chain
from os.path import exists
from pyvis.network import Network
from requests import get


def add_node(id_, image_link):
	source = 'https://wiki.factorio.com'
	local_link = 'img/'+image_link.split('/')[-1]
	if not exists(local_link):
		with open(local_link, 'wb') as f:
			f.write(get(source+image_link).content)

	if id_ not in net.node_ids:
		net.add_node(id_, shape='image', image=local_link)


def get_science_pack_info(pack_details, last_pack=False):
	type_ = pack_details.find_all('td')[last_pack]
	id_ = type_.find_all('a')[last_pack].get('href')[1:]
	image_link = type_.find_all('a')[last_pack].find('img').get('src')
	add_node(id_, image_link)
	return id_


def study_recipe(head_id):
	source = 'https://wiki.factorio.com'
	container = BeautifulSoup(get(source+'/'+head_id).text, 'html.parser')
	try:
		container = container.find_all('div', {'class':'tabbertab'})[0]
		# [0] Recipe, [1] Total raw
		container = container.find_all('td', {'class':'infobox-vrow-value'})[0]
		container = container.find_all('a')
	except IndexError:
		return []
	
	if container: # presence of recipe
		recipe_required = []
		for recipe_item in container[1:-1]:
			id_ = recipe_item.get('href')[1:]
			image_link = recipe_item.find('img').get('src')
			add_node(id_, image_link)
			net.add_edge(id_, head_id)
			recipe_required.append(id_)
		return recipe_required
	return []


def max_distance(A, targets):
	neighbors, max_distance, i = [A], 0, 0

	while neighbors:
		neighbors = list(chain(*map(net.neighbors, neighbors)))
		i+=1
		if any(map(lambda e: e in targets, neighbors)):
			max_distance = i
	return max_distance


def set_position(node,x,y):
	net.node_map[node]['x'] = x
	net.node_map[node]['y'] = y


if __name__ == "__main__":
	X_DISTANCE, Y_DISTANCE, processed_recipes = 200, 200, set()

	net = Network('100%', '100%', directed=True)
	net.toggle_physics(False)

	text = get('https://wiki.factorio.com/Science_pack').text
	soup = BeautifulSoup(text, 'html.parser')
	types_table = soup.find('table', {'class':'wikitable'})
	packs = types_table.find_all('tr')[1:]

	recipe_required = list(map(get_science_pack_info, packs[:-1]))
	recipe_required.append(get_science_pack_info(packs[-1], last_pack=True))
	science_packs = list(recipe_required)

	while recipe_required:
		recipe_required = [id_ for id_ in recipe_required 
								if id_ not in processed_recipes]
		processed_recipes.update(recipe_required)
		recipe_required = list(chain(*map(study_recipe, recipe_required)))

	# improve data representation
	level = dict()
	for node in net.node_ids:
		level_i = max_distance(node, science_packs)
		if (l_content:=level.get(level_i)):
			l_content.append(node)
		else:
			level.update([(level_i, [node])])

	for y in level.keys():
		columns = len(level[y])
		for x in range(columns):
			set_position(level[y][x], 
						 x*X_DISTANCE-columns*X_DISTANCE/2, 
						 y*Y_DISTANCE)

	# usage table construction
	usage_table, nodes_info = '''
	<html><head><title>connectivity table</title></head>
	<body><table><tr><th>item</th><th>total</th><th>used in</th><tr>''', []
	for node in net.node_ids:
		if node not in science_packs:
			img = net.node_map[node]['image']
			connections = len(net.neighbors(node))
			usage = sorted(net.neighbors(node), 
						   key=lambda n: len(net.neighbors(n)), 
						   reverse=True)
			usage = map(lambda n: net.node_map[n]['image'], usage)
			nodes_info.append((img, connections, usage))
	for img, connections, usage in sorted(nodes_info, 
										  key=lambda n: n[1], 
										  reverse=True):
		usage_table+=f'''
			<tr>
			<td><img src="{img}"></td>
			<td><center>{connections}</center></td>
			<td>{''.join(f'<img src="{png}">' for png in usage)}</td>
			</tr>
			'''
	with open('usage_table.html', 'w') as f:
		usage_table+='</table></body></html>'
		f.write(usage_table)

	net.show('recipe_tree.html')
