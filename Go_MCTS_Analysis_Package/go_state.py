import numpy as np

class GoGame:
    def __init__(self, size=5, komi=7.5):
        self.board = np.zeros((size, size), dtype=int)
        self.board_history = [self.board.copy()]
        self.current_player = 1
        self.turn_count = 0
        self.consecutive_passes = 0
        self.game_over = False
        self.komi = komi

    def getneighbours(self,row,column):
        possible_neighbours = [
            (row-1,column),
            (row+1,column),
            (row,column-1),
            (row,column+1)
        ]       

        neighbours = []

        for neighbour_row , neighbour_column in possible_neighbours:
            if 0 <= neighbour_row < self.board.shape[0] and 0<=neighbour_column<self.board.shape[1]:
                neighbours.append((neighbour_row,neighbour_column))
        return neighbours

    def getliberties(self,row,column):
        liberties = []

        for liberty_row , liberty_column in self.getneighbours(row,column):
            if self.board[liberty_row,liberty_column]==0:
                liberties.append((liberty_row,liberty_column))

        return liberties

    def getgroup_liberties(self,row,column):
        colour = self.board[row,column]
        if colour==0:
            return [],[]
        
        
        group_liberties=[]
        group = [(row,column)]
        to_check = [(row,column)]
        for r,c in to_check:
            for liberty in self.getliberties(r,c):
                if liberty not in group_liberties:
                    group_liberties.append(liberty)

            for nr,nc in self.getneighbours(r,c):
                if self.board[nr,nc]==colour:
                    if (nr,nc) not in group:
                        group.append((nr,nc))
                        to_check.append((nr,nc))
        
        
        
        return group, group_liberties
    def capture(self,row,column,player):
        opponent=3-player

        for r,c in self.getneighbours(row,column):
            if self.board[r,c]==opponent:
                group,liberties=self.getgroup_liberties(r,c)

                if len(liberties)==0:
                    for stone_row,stone_column in group:
                        self.board[stone_row,stone_column]=0

    def place(self, row, column):
            if self.game_over:
                    return False

            if not (0 <= row < self.board.shape[0]
                    and 0 <= column < self.board.shape[1]):
                return False

            if self.board[row, column] != 0:
                return False

            previous_boardstate= self.board.copy()

            self.board[row, column] = self.current_player
            self.capture(row, column, self.current_player)

            group, liberties = self.getgroup_liberties(row, column)

            if len(liberties) == 0:
                self.board[:] = previous_boardstate
                return False

            for previous_board in self.board_history:
                 if np.array_equal(self.board, previous_board):
                    self.board[:] = previous_boardstate
                    return False

            self.board_history.append(self.board.copy())
            self.consecutive_passes = 0
            self.turn_count += 1
            self.current_player = 3 - self.current_player
            return True
    def pass_move(self):
        if self.game_over:
            return False

        self.consecutive_passes += 1
        self.turn_count += 1
        self.current_player = 3 - self.current_player

        if self.consecutive_passes == 2:
            self.game_over = True

        return True
    def areascoring(self):
        empty_regions = []
        visited = set()
        black_area=[]
        white_area=[]
        neutral_area=[]


        for row in range(self.board.shape[0]):
            for column in range(self.board.shape[1]):
                if self.board[row, column] == 0 and (row, column) not in visited:
                    empty_region = [(row, column)]
                    to_check = [(row, column)]
                    visited.add((row, column))

                    for r, c in to_check:
                        for nr, nc in self.getneighbours(r, c):
                            if self.board[nr, nc] == 0 and (nr, nc) not in visited:
                                empty_region.append((nr, nc))
                                to_check.append((nr, nc))
                                visited.add((nr, nc))

                    empty_regions.append(empty_region)

        for region in empty_regions:
            border_colours=set()
            for a,b in region:
                for na,nb in self.getneighbours(a,b):
                    if self.board[na,nb]!=0:
                        border_colours.add(self.board[na,nb])

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
    def stone_score(self):
        black_stones=[]
        white_stones=[]
        for row in range(self.board.shape[0]):
                for column in range(self.board.shape[1]):
                    if self.board[row,column]==1:
                        black_stones.append([row,column])
                    elif self.board[row,column]==2:
                        white_stones.append([row,column])
        black_stone_score=len(black_stones)
        white_stone_score=len(white_stones)
        return black_stone_score,white_stone_score
    
    def score(self):
        if self.game_over==False:
            return None

        black_stones, white_stones = self.stone_score()
        black_area, white_area, neutral_area = self.areascoring()

        black_total = black_stones + black_area
        white_total = white_stones + white_area + self.komi

        return black_total, white_total
    
    
    
    def copy(self):
        new_game = GoGame(
            size=self.board.shape[0],
            komi=self.komi
        )

        new_game.board = self.board.copy()

        new_game.board_history = []
        for previous_board in self.board_history:
            new_game.board_history.append(previous_board.copy())

        new_game.current_player = self.current_player
        new_game.turn_count = self.turn_count
        new_game.consecutive_passes = self.consecutive_passes
        new_game.game_over = self.game_over

        return new_game
    def legal_moves(self):
        if self.game_over==True:
            return []

        moves = [None]  

        for row in range(self.board.shape[0]):
            for column in range(self.board.shape[1]):
                if self.board[row, column] == 0:
                    trial_game = self.copy()

                    if trial_game.place(row, column):
                        moves.append((row, column))

        return moves