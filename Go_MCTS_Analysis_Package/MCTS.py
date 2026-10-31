import math
from go_state import GoGame
import random
from random_agent import random_move
class Node:
    def __init__(self, game, parent=None, move=None):
        self.game = game
        self.parent = parent
        self.move = move

        self.children = []
        self.visits = 0
        self.wins = 0.0

        self.player_just_moved = 3 - game.current_player
        self.untried_moves = game.legal_moves()
    def expand(self):
        if self.untried_moves==False:
            return None

        move = random.choice(self.untried_moves)
        self.untried_moves.remove(move)

        next_game = self.game.copy()

        if move is None:
            next_game.pass_move()
        else:
            row, column = move
            next_game.place(row, column)

        child = Node(next_game, parent=self, move=move)
        self.children.append(child)

        return child
    def simulate(self,max_moves=2000):
        trial_game = self.game.copy()
        moves_played = 0
        while trial_game.game_over==False and moves_played < max_moves:
            move = random_move(trial_game)
            if move is None:
                trial_game.pass_move()
            else:
                row,column = move
                trial_game.place(row,column)
            moves_played +=1
        if trial_game.game_over==False:
            return None

        black_score,white_score = trial_game.score()

        if black_score>white_score:
            return 1
        elif white_score>black_score:
            return 2
        else:
            return 0
    def backpropagate(self,winner):
        if winner is None:
            return
        node = self

        while node is not None:
            node.visits+=1

            if winner ==0:
                node.wins +=0.5
            elif winner==node.player_just_moved:
                node.wins +=1
            node = node.parent
    def best_child(self):
        def uct(child):
            if child.visits == 0:
                return float("inf")
            win_rate = child.wins / child.visits

            exploration = math.sqrt(
                2*math.log(self.visits)/child.visits
            )
            return win_rate + exploration
        return max(self.children,key=uct)

def mcts_move(game,iterations=100):
    if game.game_over==True:
        raise ValueError("The game has already ended")
    if iterations <1:
        raise ValueError("Use at least one search iteration")

    root = Node(game.copy())
    for _ in range(iterations):
        node = root

        while not node.untried_moves and node.children:
            node = node.best_child()

        if node.untried_moves:
            node = node.expand()

        winner = node.simulate()

        if winner is None:
            raise RuntimeError(
                "A simulation reached its move limit without finishing"
            )
        node.backpropagate(winner)

    best=max(root.children,key=lambda child: child.visits)
    return best.move

if __name__ == "__main__":
    from time import perf_counter

    game = GoGame(size=5, komi=7.5)

    start = perf_counter()
    move = mcts_move(game, iterations=100)
    elapsed = perf_counter() - start

    print("Suggested move:", move)
    print(f"Search took {elapsed:.3f} seconds")