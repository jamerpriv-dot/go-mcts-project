from time import perf_counter
import random
from go_state import GoGame


def random_move(game):
    candidates = [None]

    for row in range(game.board.shape[0]):
        for column in range(game.board.shape[1]):
            if game.board[row, column] == 0:
                candidates.append((row, column))

    random.shuffle(candidates)

    for move in candidates:
        if move is None:
            return None

        row, column = move
        trial_game = game.copy()

        if trial_game.place(row, column):
            return move
if __name__ == "__main__":
    start=perf_counter()
    game = GoGame(size=5, komi=7.5)
    max_turns = 500

    while game.game_over==False and game.turn_count < max_turns:
        move = random_move(game)

        if move is None:
            game.pass_move()
        else:
            row, column = move
            game.place(row, column)

    if game.game_over==True:
        print("Final board:")
        print(game.board)
        print("Scores:", game.score())
        print("Turns:", game.turn_count)
    else:
        print("Turn limit reached: game unfinished.")

    elapsed = perf_counter() - start
    print(f"Game took {elapsed:.3f} seconds")