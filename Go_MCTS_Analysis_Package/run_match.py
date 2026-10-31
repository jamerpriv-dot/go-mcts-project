from go_state import GoGame
from MCTS import mcts_move
from time import perf_counter

game = GoGame(size=5,komi=7.5)
max_turns = 500
start=perf_counter()

while not game.game_over and game.turn_count < max_turns:
    player = game.current_player
    move=mcts_move(game,iterations=100)

    if move is None:
        accepted = game.pass_move()
    else:
        row,column = move
        accepted = game.place(row,column)

    if not accepted:
        raise RuntimeError("Mcts returned an illegal move")

    print(f"turn {game.turn_count}: player {player} played {move}")

elapsed=perf_counter()-start

print("Final board:")
print(game.board)

if game.game_over:
    black_score, white_score = game.score()
    print(f"Black: {black_score}, White: {white_score}")

    if black_score>white_score:
        print("Black wins!")
    elif white_score > black_score:
        print("White wins!")

    else:
        print("Draw")
else:
    print("Turn limit reached: game unfinished")

print(f"Turns: {game.turn_count}")
print(f"Time: {elapsed:.2f} seconds")