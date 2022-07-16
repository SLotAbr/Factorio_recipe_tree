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
						 y*y_DISTANCE)

	net.show('recipe_tree.html')
