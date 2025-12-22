import numpy as np
import numpy as np 

def heuristics_v2(Positions, Best_pos, Best_score, rg):
    SearchAgents_no = Positions.shape[0]
    dim = Positions.shape[1]

    lb_array = np.zeros((SearchAgents_no, dim))
    ub_array = np.ones((SearchAgents_no, dim))

    rand_adjust = lb_array + (ub_array - lb_array) * np.random.rand(*Positions.shape)
    Positions = np.where((Positions < lb_array) | (Positions > ub_array), rand_adjust, Positions)

    #EVOLVE-START
    beta = 1.5
    u = np.random.normal(0, 1, (SearchAgents_no, dim))
    v = np.random.normal(0, 1, (SearchAgents_no, dim))
    step = 0.01 * u / np.power(np.abs(v), 1/beta) * (Positions - Best_pos)
    
    adaptive_rg = rg * np.exp(-Best_score/1000)
    exploration_mask = np.random.rand(SearchAgents_no, 1) < adaptive_rg
    opposition = lb_array + ub_array - Positions
    Positions = np.where(exploration_mask, Positions + step, 0.6*Best_pos + 0.4*opposition)
    #EVOLVE-END       

    return Positions
