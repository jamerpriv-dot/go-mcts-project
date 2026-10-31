#go board#

import numpy as np
board = np.zeros((5,5),dtype=int)
board_history = [board.copy()]
current_player=1
turn_count=0
consecutive_passes=0
game_over = False
game_scoring=[]
game_results=[]
def pass_move():
    global current_player,turn_count,consecutive_passes,game_over
    if game_over==True:
        return False
    consecutive_passes+=1
    turn_count+=1
    current_player=3-current_player

    if consecutive_passes == 2:
        game_over= True
        game_scoring.append(score())
        game_results.append(gamewinner())
    return True


def getneighbours(row,column):
    possible_neighbours = [
        (row-1,column),
        (row+1,column),
        (row,column-1),
        (row,column+1)
    ]       

    neighbours = []

    for neighbour_row , neighbour_column in possible_neighbours:
        if 0 <= neighbour_row < 5 and 0<=neighbour_column<5:
            neighbours.append((neighbour_row,neighbour_column))

    return neighbours
def getliberties(row,column):
    liberties = []

    for liberty_row , liberty_column in getneighbours(row,column):
        if board[liberty_row,liberty_column]==0:
            liberties.append((liberty_row,liberty_column))

    return liberties

def getgroup_liberties(row,column):
    colour=board[row,column]
    if colour==0:
        return [],[]
    
    
    group_liberties=[]
    group = [(row,column)]
    to_check = [(row,column)]
    for r,c in to_check:
        for liberty in getliberties(r,c):
            if liberty not in group_liberties:
                group_liberties.append(liberty)

        for nr,nc in getneighbours(r,c):
            if board[nr,nc]==colour:
                if (nr,nc) not in group:
                    group.append((nr,nc))
                    to_check.append((nr,nc))
    
    
    
    return group, group_liberties

def capture(row,column,player):
    opponent=3-player

    for r,c in getneighbours(row,column):
        if board[r,c]==opponent:
            group,liberties=getgroup_liberties(r,c)

            if len(liberties)==0:
                for stone_row,stone_column in group:
                    board[stone_row,stone_column]=0


def ask_move():
    row = int(input("Row (1-5):\n"))-1
    column = int(input("Column (1-5):\n"))-1
    return row, column

def game_start():
    players = [1,2]
    turn = 0
    while np.any(board == 0):
        print(f"Player {players[turn]}'s turn")

        row,column = ask_move()
        if place(row,column,players[turn]):
            print(board)
            turn=1-turn
        if game_over==True:
            break




def place(row,column,player):
    global consecutive_passes, turn_count, current_player
    if game_over==True:
        return False
    if 0 <= row <5 and 0 <= column <5:
        if board[row,column]==0:
            previous_boardstate=board.copy()
            board[row,column] = player
            capture(row,column,player)
    
            group,liberties = getgroup_liberties(row,column)
            if len(liberties)==0:
                board[:]=previous_boardstate
                print("Suicide is against the rules")
            else:
                for previous_board in board_history:
                    if np.array_equal(board, previous_board):
                        board[:] = previous_boardstate
                        print("Repeating a board position is against the rules")
                        return False

                board_history.append(board.copy())
                consecutive_passes = 0
                turn_count+=1
                current_player=3-current_player
                return True
        else:
            print("Occupied")
    else: 
        print("Must be placed inside board.")
    return False  

def areascoring():
    empty_regions = []
    visited = set()
    black_area=[]
    white_area=[]
    neutral_area=[]


    for row in range(board.shape[0]):
        for column in range(board.shape[1]):
            if board[row, column] == 0 and (row, column) not in visited:
                empty_region = [(row, column)]
                to_check = [(row, column)]
                visited.add((row, column))

                for r, c in to_check:
                    for nr, nc in getneighbours(r, c):
                        if board[nr, nc] == 0 and (nr, nc) not in visited:
                            empty_region.append((nr, nc))
                            to_check.append((nr, nc))
                            visited.add((nr, nc))

                empty_regions.append(empty_region)

    for region in empty_regions:
        border_colours=set()
        for a,b in region:
            for na,nb in getneighbours(a,b):
                if board[na,nb]!=0:
                    border_colours.add(board[na,nb])

        if border_colours=={1}:
            black_area.extend(region)
        elif border_colours=={2}:
            white_area.extend(region)
        else:
            neutral_area.extend(region)

    black_area_score=len(black_area)
    white_area_score=len(white_area)
    neutral_area_score=len(neutral_area)
    return black_area_score,white_area_score,neutral_area_score    


def stone_score():
    black_stones=[]
    white_stones=[]
    for row in range(board.shape[0]):
            for column in range(board.shape[1]):
                if board[row,column]==1:
                    black_stones.append([row,column])
                elif board[row,column]==2:
                    white_stones.append([row,column])
    black_stone_score=len(black_stones)
    white_stone_score=len(white_stones)
    return black_stone_score,white_stone_score

def score(komi=7.5):
    if game_over==True:
        black_total_score = stone_score()[0] + areascoring()[0]
        white_total_score = stone_score()[1] + areascoring()[1] + komi
        return black_total_score,white_total_score

    
def gamewinner():
    black_score=0
    white_score=0
    
    if game_over==True:
        if score()[0]>score()[1]:
            black_score=black_score+1
        elif score()[1]>score()[0]:
            white_score=white_score+1
        
        
        return black_score,white_score
def win_tally():
    black_wins=sum(result[0]for result in game_results)
    white_wins=sum(result[1]for result in game_results)
    return black_wins,white_wins



def reset_game():
    global current_player, turn_count, consecutive_passes, game_over

    board[:] = 0
    board_history.clear()
    board_history.append(board.copy())
    current_player = 1
    turn_count = 0
    consecutive_passes = 0
    game_over = False




   

