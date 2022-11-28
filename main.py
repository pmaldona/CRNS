from typing import Union, Any
import eel
from src.Simulation.Simulation import plot_abstractions_callable, plot_df, plot_hist_simple_rw, plot_markov_callable, plot_random_walk_callable, plot_stoich, plot_trajectory_callable
from src.Network.Network import get_network_from_set
from src.store.Store import State

print("[eel]: Init");

eel.init('static')

state = State()

@eel.expose                         # Expose this function to Javascript
def say_hello_py(x):
    print('Hello from %s' % x)

@eel.expose
def has_loaded_file():
    rn = state.get_current_state()["RN"]
    print(rn)
    return rn != None

@eel.expose
def get_network(species_set):
    get_network_from_set(species_set)

@eel.expose
def openFile(path) -> bool:
    return state.open_file(str(path))
    

@eel.expose
def export_network(path: str):
    if state.reaction_network != None:
        return state.save_network(path)
    else:
        return False
    
@eel.expose
def gen_network() -> Union[dict[str, Any], None]:
    network = state.get_network()
    if network != None:
        nodes, edges, heading, height, width, options = network.get_network_data()
        return {"nodes": nodes, "edges": edges, "heading": heading, "height": height, "width": width, "options": options}
    else:
        return None

@eel.expose
def gen_synergetic():
    network = state.get_synergetic_structure()
    if network != None:
        nodes, edges, heading, height, width, options = network.get_network_data()
        return {"nodes": nodes, "edges": edges, "heading": heading, "height": height, "width": width, "options": options}
    else:
        return None

@eel.expose
def gen_protosynergetic():
    network = state.get_protosynergetic_structure()
    if network != None:
        nodes, edges, heading, height, width, options = network.get_network_data()
        return {"nodes": nodes, "edges": edges, "heading": heading, "height": height, "width": width, "options": options}
    else:
        return None

@eel.expose
def calculate_orgs():
    network = state.get_hasse_structure()
    if network != None:
        nodes, edges, heading, height, width, options = network.get_network_data()
        return {"nodes": nodes, "edges": edges, "heading": heading, "height": height, "width": width, "options": options}
    else:
        return None

@eel.expose
def get_reactions():
    return state.get_reactions()

@eel.expose
def plot_stoichiometry():
    network = state.reaction_network
    if network != None:
        plot = network.plotS(return_figure=True)
        return plot_stoich(plot)
    else:
        return None

@eel.expose
def plot_concentrations(SpConFileNameStr=None, KConstFileNameStr=None, ti=0, tf=50, steps=100, cutoff=0.1):
    model = state.get_concentrations_run(SpConFileNameStr, KConstFileNameStr, ti, tf, steps, cutoff)
    if model != None:
        return plot_df(model, title="Concentrations")
    else:
        return None

@eel.expose
def plot_rates(SpConFileNameStr=None, KConstFileNameStr=None, ti=0, tf=50, steps=100, cutoff=0.1):
    model = state.get_rates_run(SpConFileNameStr, KConstFileNameStr, ti, tf, steps, cutoff)
    if model != None:
        return plot_df(model, title="Rates")
    else:
        return None
    
@eel.expose
def random_network(has_inflow= False, random_species= 2, random_reactions= 2, extra=0.4, distribution= "x*0+1", pr= 0, pp= 0, inflow= 0.1, outflow= 0.1):
    print(random_species)
    return state.generate_random_network(has_inflow, random_species, random_reactions, extra, distribution, pr, pp, inflow, outflow)

@eel.expose
def add_extra_species(Nse=None,p=0.1,extra=None,m=1, l="x"):
    return state.add_species(Nse=Nse, p=p, extra=extra, m=m, l=l)

@eel.expose
def add_inflow(extra=0.1):
    return state.add_inflow(extra)

@eel.expose
def add_outflow(extra=0.1):
    return state.add_outflow(extra)

@eel.expose
def simple_random_walk(w, l, d, nmin, fname):
    rn = state.reaction_network
    if rn != None:
        keys = state.get_simple_rw(range(w), l, d, nmin, fname)
        if keys != None:
            return list(keys)
        else:
            return False
    else:
        return False

@eel.expose
def plot_simple_random_walk_raw(index) -> Union[str, bool]:
    if state.reaction_network == None:
        return False
    else:
        if state.simple_rw == False:
            if state.init_simple_random_walk() == False:
                return False
        return plot_random_walk_callable(state.reaction_network.plotRawSimpleRw, index)

@eel.expose
def plot_abstraction(index):
    if state.reaction_network == None:
        return False
    else:
        if state.simple_rw == False:
            if state.init_simple_random_walk() == False:
                return False
        plot = plot_abstractions_callable(state.reaction_network.plotChangeSimpleRw, index)
        return plot

@eel.expose
def plot_trajectory(index, conv_pert, title=''):
    if state.reaction_network == None:
        return False
    else:
        if state.simple_rw == False:
            if state.init_simple_random_walk() == False:
                return False
        if conv_pert == True:
            return plot_trajectory_callable(state.reaction_network.plotHasseConvergenceAndPerturbationSimpleRw,conv_pert, index)
        else:
            return plot_trajectory_callable(state.reaction_network.plotHasseSimpleRw, conv_pert, index)

@eel.expose
def plot_histogramm_random_walk():
    if state.reaction_network == None:
        return False
    else:
        if state.simple_rw == False:
            if state.init_simple_random_walk() == False:
                return False
        return plot_hist_simple_rw(state.reaction_network.plotHistSimpleRw)

@eel.expose
def plot_markov():
    if state.reaction_network == None:
        return False
    else:
        if state.simple_rw == False:
            if state.init_simple_random_walk() == False:
                return False
        return plot_markov_callable(state.reaction_network.plotMarkovSimpleRw)


print("[eel]: Start");

eel.start('index.html', mode=None)


# basic = 0
#         closed = 0
#         basic_closed = 0
#         ssm = 0
#         orgs = 0
#         union = 0
#         syn_union = 0
#         conn_orgs = 0
#         for node in nodes:
#             if node['shape'] == 'dot':
#                 basic = basic + 1
#             elif node['shape'] == 'square':
#                 closed = closed + 1
#             if node['color'] == 'red':
#                 basic_closed = basic_closed + 1
#             elif node['color'] == 'blue':
#                 ssm = ssm + 1
#             elif node['color'] == 'green':
#                 orgs = orgs + 1
#         for edge in edges:
#             if edge['color'] == 'green':
#                 union = union + 1
#             elif edge['color'] == 'blue':
#                 syn_union = syn_union + 1
#transitions = 0 #len(RN.getSyn())
#        generators = len(nodes) - transitions