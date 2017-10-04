"""Chess program that either accepts human player's input moves or 
randomly selects moves"""

import random, copy, time, cProfile

not_on_board = [10*i for i in range(2,10)] + [10*i+9 for i in range(2,10)]
on_board = [square for square in range(20,100) if square not in not_on_board]

col_dict = {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f", 7: "g", 8: "h"}
col_dict_ = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}
piece_dict = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
piece_dict_ = {"P": 1, "N": 2, "B": 3, "R": 4, "Q": 5, "K": 6}

#maps piece representations to values
value_dict = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 0}

def initialise_board():
    """creates initial chess position"""
    board = [0]*120 #empty chess board
    
    edges = range(20)
    edges += range(100,120)
    edges += [10 * n for n in range(2,10)]
    edges += [10 * n + 9 for n in range(2,10)]
    #print edges
    
    for i in edges:
        board[i] = 100
    
    #fill with white pieces (initial position)
    board[21] = 4
    board[22] = 2
    board[23] = 3
    board[24] = 5
    board[25] = 6
    board[26] = 3
    board[27] = 2
    board[28] = 4
    for i in range(31,39):
        board[i] = 1
        
    #fill with black pieces (initial position)    
    board[91] = -4
    board[92] = -2
    board[93] = -3
    board[94] = -5
    board[95] = -6
    board[96] = -3
    board[97] = -2
    board[98] = -4
    for i in range(81,89):
        board[i] = -1
    return board

initial_board = initialise_board()


class Position(object):
    """A chess position complete with history"""
    def __init__(self,board,turn = "white",move_seq = [],position_hashes = None,h = None,\
    num_pieces = 32,old_num_pieces = None,pawn_moved = None,fifty_move_counter = 0,in_check = None,castling = False,num = 1):
        self.board = board
        self.turn = turn
        self.sgn = 1 if self.turn == "white" else -1
        self.move_seq = move_seq
        self.num = num
        if position_hashes == None:
            self.position_hashes = {hash(tuple(board)+tuple([turn])): 1}
        else:
            self.position_hashes = position_hashes
        if h == None:
            self.h = hash(tuple(board)+tuple([turn]))
        else:
            self.h = h
        self.num_pieces = num_pieces
        self.old_num_pieces = old_num_pieces
        self.pawn_moved = pawn_moved
        self.fifty_move_counter = fifty_move_counter
        self.in_check = in_check
        self.castling = castling #was last move castling move?
    
    #make rollback method: just keep track of past board positions, infer other attributes from there                                         
                                                                                                                               
    def print_board(self):
        """prints board using numbers"""
        for i in range(12):
            j = 11-i
            print self.board[10*j:10*(j+1)]

    def print_board2(self):
        """prints board using letters and without the edges"""
        d = {-6: "bK",
        -5: "bQ",
        -4: "bR",
        -3: "bB",
        -2: "bN",
        -1: "bP",
        0: "  ",
        1: "wP",
        2: "wN",
        3: "wB",
        4: "wR",
        5: "wQ",
        6: "wK"}
        for i in range(8):
            j = 9-i
            line = str(j-1)+" |"
            for k in range(10*j+1,10*j+9):
                line += d[self.board[k]]
                line += " |"
            print line
        print "   a   b   c   d   e   f   g   h"

    def make_move(self,move,verbose = False, update_in_check = True, just_board = False):
        """execute a move on the board"""
        
        if move is not None:          
            castling = True if abs(self.board[move[0]]) == 6 and abs(move[1]-move[0]) in (2,3) else False           
            if not just_board:
                #will other player be in check?                
                if update_in_check:
                    self.in_check = self.check_check(move,castling)
                
                self.move_seq.append(move)
                if verbose:
                    print "Move =", printable_move(move)
                    #print move_seq
                
                self.castling = castling
                
                #50 move rule: updating counter if no pawn has moved and a piece has not been captured 
                self.pawn_moved = (abs(self.board[move[0]]) == 1)
                self.old_num_pieces = self.num_pieces
            
            #if pawn promotes
            if len(move) > 2:
                self.board[move[1]] = self.sgn * move[2]
            #elif pawn takes en passant (i.e. pawn moves one square diagonally to an empty square)
            elif abs(self.board[move[0]]) == 1 and abs(move[1]-move[0]) in (9,11) and self.board[move[1]] == 0:   
                self.board[move[1]] = self.board[move[0]]
                if just_board:
                    captured_pawn_on = self.move_seq[-1][1]
                else:
                    captured_pawn_on = self.move_seq[-2][1]
                self.board[captured_pawn_on] = 0
            #elif castling
            elif castling:
                self.board[move[1]] = self.board[move[0]] #king move
                #rook move
                if move[0] == 25:
                    if move[1]-move[0] == 2: #white kingside
                        self.board[26] = 4
                        self.board[28] = 0
                    else: #white queenside
                        self.board[24] = 4
                        self.board[21] = 0
                else:
                    if move[1]-move[0] == 2: #black kingside
                        self.board[96] = -4
                        self.board[98] = 0
                    else: #black queenside
                        self.board[94] = -4
                        self.board[91] = 0   
            else:
                self.board[move[1]] = self.board[move[0]]
            self.board[move[0]] = 0
        
        if not just_board:    
            self.num_pieces = sum(1 if self.board[square] != 0 else 0 for square in on_board)
            self.h = hash(tuple(self.board)+tuple([self.turn]))
            #print "hash=",h
            if self.h not in self.position_hashes:
                self.position_hashes[self.h] = 1
            else:
                self.position_hashes[self.h] += 1           
            if verbose:
                #print board
                self.print_board2(self.board)
            self.num += 1
            if verbose:
                print "\n"
                
        self.turn = "black" if self.turn == "white" else "white"
        self.sgn = 1 if self.turn == "white" else -1                  
        
    def calc_offsets(self,piece,pos,with_castling = True,in_check = None):
        """determine potential offsets for a given piece type on a certain position on the board"""
        #print "calc offsets"
        #print "piece=", piece
        #print "pos=",pos
        piece_sgn = 1 if self.board[pos] > 0 else -1
        
        #knight
        if piece == 2:
            if pos % 10 == 1: #knight on a file
                offsets = [21,19,12,-21,-19,-8]
            elif pos % 10 == 8: #knight on h file
                offsets = [21,19,8,-21,-19,-12]
            else:
                offsets = [21,19,8,12,-21,-19,-8,-12] #knight somewhere else
        #king
        elif piece == 6: 
            offsets = [-11,-10,-9,-1,1,9,10,11]
            if with_castling:
                #check that king has not moved, rook is on original square, \
                #all squares inbetween are empty, king is not in check
                sq = 25 if piece_sgn == 1 else 95
                if sq not in (move[0] for move in self.move_seq) and not self.king_hanging(move = None):
                    #kingside castling
                    if abs(self.board[sq+3]) == 4\
                    and self.board[sq+1] == 0 and self.board[sq+2] == 0:
                    #check that king wouldn't castle over attacked square
                        if not self.king_hanging((sq,sq+1))\
                        and not self.king_hanging((sq,sq+2)):
                            #add castling to offsets
                            offsets.append(2)
                            #print pos,sq
                    #queenside castling
                    if abs(self.board[sq-4]) == 4\
                    and self.board[sq-1] == 0 and self.board[sq-2] and self.board[sq-3] == 0:              
                        #check that king wouldn't castle over attacked square
                        if not self.king_hanging((sq,sq-1))\
                        and not self.king_hanging((sq,sq-2))\
                        and not self.king_hanging((sq,sq-3)):
                            #add castling to offsets
                            offsets.append(-2)
                            #print pos,sq
        #pawn
        elif piece == 1:
            a = 56 - piece_sgn*25
            b = 64 - piece_sgn*25
            offsets = []
            if self.board[pos + piece_sgn*10] == 0:
                offsets.append(piece_sgn*10)
                if pos in range(a,b) and self.board[pos + piece_sgn*20] == 0:
                    offsets.append(piece_sgn*20)
            #if can capture diagonally or en passant, add offset
            c = 56 + 5*piece_sgn
            d = 64 + 5*piece_sgn
            #topleft or bottomright
            if piece_sgn * self.board[pos + piece_sgn*9] < 0:
                offsets.append(self.sgn*9)
            elif len(self.move_seq) >0:
                if (pos in range(c,d) and self.move_seq[-1] == (pos+piece_sgn*19,pos-piece_sgn) and self.board[pos-piece_sgn] == -1*piece_sgn): #pawn to the left
                    offsets.append(piece_sgn*9)
            #topright or bottomleft
            if piece_sgn * self.board[pos + piece_sgn*11] < 0:
                offsets.append(piece_sgn*11) 
            elif len(self.move_seq) >0:
                if (pos in range(c,d) and self.move_seq[-1] == (pos+piece_sgn*21,pos+piece_sgn) and self.board[pos+piece_sgn] == -1*piece_sgn): #pawn to the right
                    offsets.append(piece_sgn*11)
        else:
            #bishop
            if piece == 3:
                directions = [11,-11,9,-9]
                #11 is topright direction, -11 is bottomleft, 9 is topleft, -9 is bottomright
            #rook
            elif piece == 4:
                directions = [10,-10,1,-1] #10 is up, -10 is down, 1 is right, -1 is left
            #queen
            elif piece == 5: 
                directions = [11,-11,9,-9, 10,-10,1,-1] #bishop and rook directions            
            offsets = []
            for d in directions:
                i = 1
                while piece_sgn * self.board[pos + d*i] <= 0:
                    offsets.append(d*i)
                    if piece_sgn * self.board[pos + d*i] < 0:
                        break
                    else:
                        i += 1
        return offsets  


    def attacks(self,a,b):
        """returns True if there is a piece on square a attacking square b"""    
        piece = self.board[a]
        if piece == 0:
            #print "piece is 0"
            return False
        sgn = 1 if piece > 0 else -1
        if abs(piece) != 1:
            #print "b=",b
            #print "a=",a
            return b-a in self.calc_offsets(sgn*piece,a,with_castling = False) 
        else:
            return b-a in (sgn*9,sgn*11)    


    def is_attacked(self,square):
        """returns True if square is attacked by player whose turn it is"""
        #check whether there are pawns diagonally opposite or knights an L-offset away or king adjacent
        #then check along rows/columns (rooks, queens) and diagonals (bishops, queens) until hit a piece
        for direction in [10,-10,-1,1]: #check rows and colums (up, down, left, right)
            new_sq = square + direction
            while new_sq in on_board:
                if self.board[new_sq] in (4*self.sgn,5*self.sgn):
                    #print "new_sq=",new_sq
                    #print "on board=",self.board[new_sq]
                    #print "sgn in is_attacked=",self.sgn
                    #print "row/col"
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction
    
        for direction in [9,-9,11,-11]: #check diagonals (up left, down right, up right, down left)
            new_sq = square + direction
            while new_sq in on_board:
                if self.board[new_sq] in (3*self.sgn,5*self.sgn):
                    #print "diag"
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction
        
        for offset in [-9*self.sgn,-11*self.sgn]: #check pawns
            new_sq = square+offset
            if self.board[new_sq] == self.sgn:
                #print "pawn"
                return True
        
        for offset in [-11,-10,-9,-1,1,9,10,11]: #check king
            new_sq = square + offset
            if self.board[new_sq] == 6*self.sgn:
                #print "king"
                return True
        
        #check knights    
        if square % 10 == 1: #square on a file
            offsets = [21,19,12,-21,-19,-8]
        elif square % 10 == 8: #square on h file
            offsets = [21,19,8,-21,-19,-12]
        else:
            offsets = [21,19,8,12,-21,-19,-8,-12] #square somewhere else
        for offset in offsets:
            new_sq = square + offset
            if self.board[new_sq] == 2*self.sgn:
                #print "knight"
                return True 
    
        #if no flag is raised
        return False   

    def king_hanging(self,move):
        """checks whether, after colour's move, colour's king can be captured in a given 
        position by the other player."""
        #print "calling king_hanging with move=",move,"colour=",colour
        if move == None and self.in_check == True:
            return True
        if move == None or self.in_check != False: #in_check might be unknown
            old_board = self.board[:]
            self.make_move(move,update_in_check = False,just_board = True) #avoid infinite recursion
            kings_square = self.board.index(self.sgn* -6)
            #print kings_square
            a = self.is_attacked(kings_square)
            self.board = old_board[:]
            self.turn = "black" if self.turn == "white" else "white"
            self.sgn = 1 if self.sgn == -1 else -1
            return a
        kings_square = self.board.index(self.sgn*6)
        diff = move[0] - kings_square
        if abs(self.board[move[0]]) == 6 or diff % 9 == 0 or diff % 11 == 0 or (move[0] % 10 == kings_square % 10) or (move[0]/10 == kings_square/10): #piece might have been pinned
            old_board = self.board[:]
            self.make_move(move,update_in_check = False,just_board = True) #avoid infinite recursion
            kings_square = self.board.index(self.sgn* -6)
            #print kings_square
            a = self.is_attacked(kings_square)
            self.board = old_board[:]
            self.turn = "black" if self.turn == "white" else "white"
            self.sgn = 1 if self.sgn == -1 else -1
            return a
        return False
    
    def check_check(self,move,castling):
        """determines whether move puts other player in check. castling indicates whether move is a castling move"""

        opp_king_sq = self.board.index(-6*self.sgn)
        old_board = self.board[:]
        self.make_move(move,update_in_check = False,just_board = True)
        
        #print "move end=",move[1]
        #print "opp_king_sq=",opp_king_sq
        #print "piece on new sq?", position_copy.board[move[1]]
        
        
        def rollback():
            self.board = old_board[:]
            self.turn = "black" if self.turn == "white" else "white"
            self.sgn = 1 if self.sgn == -1 else -1
        
        if self.attacks(move[1],opp_king_sq): #if moved piece attacks opposite king, return True (includes pawn promotion case)
            #print "moved piece attacks opp king"
            rollback()
            return True
        
        #if discovery possible, check pieces on row/col/diagonal. also check castling
        diff = opp_king_sq - move[0]    
                          
        if diff % 9 == 0:
            direction = -9 if diff > 0 else 9
            new_sq = move[0] + direction
            while new_sq in on_board:
                if self.board[new_sq] in (-3*self.sgn,-5*self.sgn):
                    #print "diag1"
                    rollback()
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction    
        elif diff % 11 == 0:
            direction = -11 if diff > 0 else 11
            new_sq = move[0] + direction
            while new_sq in on_board:
                if self.board[new_sq] in (-3*self.sgn,-5*self.sgn):
                    #print "diag2"
                    rollback()
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction       
        elif move[0] % 10 == opp_king_sq % 10:
            direction = -10 if diff > 0 else 10
            new_sq = move[0] + direction
            while new_sq in on_board:
                if self.board[new_sq] in (-4*self.sgn,-5*self.sgn):
                    #print "col"
                    rollback()
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction           
        elif move[0]/10 == opp_king_sq/10:
            direction = -1 if diff > 0 else 1
            new_sq = move[0] + direction
            while new_sq in on_board:
                if self.board[new_sq] in (-4*self.sgn,-5*self.sgn):
                    #print "row"
                    rollback()
                    return True
                elif self.board[new_sq] != 0:
                    break
                else:
                    new_sq += direction        
        elif castling:
            if self.sgn == -1:
                if move[1] == 27: #kingside castling, so rook on f1
                    if self.attacks(26,opp_king_sq):
                        #print "castling"
                        rollback()
                        return True
                else: #queenside castling, so rook on d1
                    if self.attacks(24,opp_king_sq):
                        #print "castling"
                        rollback()
                        return True
            else:
                if move[1] == 97: #kingside castling, so rook on f8
                    if self.attacks(96,opp_king_sq):
                        #print "castling"
                        rollback()
                        return True
                else: #queenside castling, so rook on d8
                    if self.attacks(94,opp_king_sq):
                        #print "castling"
                        rollback()
                        return True
        #print "nothing"
        rollback()
        return False
        
    def make_move_list(self,check_for_king_hanging = True, with_castling = True):
        """list legal moves in a given position in the form: (old field,new field)
        for white: colour = "white", for black: colour = "black"
        need to be able to exclude castling moves so as to avoid 
        infinite recursion when checking whether castling puts the king in check 
        (opponent's castling needn't be considered as a response to determine 
        whether king is in check after castling)"""
        move_list = []
        #print "calling make_move_list, colour=",colour,"check_for_king_hanging=",check_for_king_hanging
        
        pairs = ((pair[0],abs(pair[1])) for pair in enumerate(self.board) if pair[0] in on_board and self.sgn*pair[1] > 0)
        for pos, piece in pairs:
            offsets = self.calc_offsets(piece,pos,with_castling)
            #print "pos=",pos,"piece=",piece
            potential_targets = [pos + offset for offset in offsets]
            potential_targets = [target for target in potential_targets if target in on_board]
            targets = (target for target in potential_targets if self.sgn*self.board[target] <= 0) if piece != 1 else potential_targets # pawns already checked
            #if pawn moves to last row (8th or 1st), promote to N/B/R/Q
            if piece == 1:
                for target in targets:
                    if target not in range(21,29)+range(91,99):
                        #print "appending: ", (pos,target)
                        move_list.append((pos,target))
                    else:
                        for promoted_to in (2,3,4,5):
                            #print "appending: ", (pos,target)
                            move_list.append((pos,target,promoted_to))
            else:
                for target in targets:
                    #print "appending: ", (pos,target)
                    move_list.append((pos,target))
            #print "move_list=",move_list
                    
        if check_for_king_hanging:
            for move in copy.copy(move_list):
                #if after move own king is in check, remove this move from the move list
                #print "checking whether king hanging after move=",move
                #print_board2(board)
                if self.king_hanging(move):
                    #print "king hanging after ",move," so removing"
                    move_list.remove(move)
        return move_list







def printable_move(move):
    """converts internal square representation to common chess notation"""
    start = move[0]
    finish = move[1]
    start_col = col_dict[start % 10]
    start_row= str(start/10-1)
    finish_col = col_dict[finish % 10]
    finish_row = str(finish/10 - 1)
    s = start_col + start_row + "-" + finish_col + finish_row
    if len(move) == 2:
        return s
    else:
        promoted_to = move[2]
        return s + piece_dict[abs(promoted_to)]


def evaluate_pos(pos,in_check = None):
    """checks for checkmate/stalemate/fifty-move rule/threefold repetition/insufficient material"""
    #print "in-check=",in_check
    reason = None
    outcome = None
    try:
        possible_moves = pos.make_move_list()
    except:
        pos.print_board2()
        seq_string = "All moves"
        i = 1
        for move in pos.move_seq:
            seq_string += (" " + str(i) + "." + printable_move(move))
            i += 1
        print seq_string
        print pos.castling
        raise ValueError
        
    
    if len(possible_moves) == 0: #no possible moves
        #if in check, checkmate
        if pos.king_hanging(None):
            reason = "checkmate"
            outcome = 0 if pos.turn == "white" else 1
        #else stalemate
        else:
            reason = "stalemate"
            outcome = 0.5
        
    #threefold repetition"
    #ignores possible hash collision. to deal with this, store list of historic
    #board positions and in the case of triple occurence of a hash value,
    #do another check of the full board positions
    elif pos.position_hashes[pos.h] == 3:
        reason = "threefold repetition"
        outcome = 0.5
        
    #if too little material on board, draw (K-K,KN-K,K-KN,KB-K,K-KB)
    elif pos.num_pieces == 2:
        reason = "insufficient material"
        outcome = 0.5
    elif pos.num_pieces == 3:
        pieces = [abs(pos.board[square]) for square in on_board if pos.board[square] != 0]
        if 2 in pieces or 3 in pieces:
            reason = "insufficient material"
            outcome = 0.5
            
    #50 move rule        
    #print "old_num_pieces=",old_num_pieces, "num_pieces=",num_pieces
    #print "pawn_moved=",pawn_moved
    elif pos.num_pieces == pos.old_num_pieces and not pos.pawn_moved:
        pos.fifty_move_counter += 1
        if pos.fifty_move_counter >= 100:
            reason = "50 move rule"
            outcome = 0.5
    else:
        pos.fifty_move_counter = 0
    return outcome, reason, possible_moves, pos.fifty_move_counter        

def tree_search(pos,depth,outcome = None, poss_moves = None, alpha = float("-inf"),beta = float("inf")):
    """evaluates all possible moves up to the depth and returns best one along with position evaluation"""
    if poss_moves == None:
        outcome, reason, poss_moves, fifty_move_counter = evaluate_pos(pos)
    #print "\n"
    #print "tree_search"
    #print "outcome=",outcome
    #print "poss_moves=",poss_moves
    #print "depth=",depth
    #print "last move " + printable_move(move_seq[-1]) if len(move_seq) > 0 else "initial position"
    
    best_move = None
    if outcome == 1:
        score = pos.sgn * 99999 #if this is inf, might not return any move if being checkmated is certain
    elif outcome == 0.5:
        score = 0
    elif outcome == 0:
        score = pos.sgn * -99999
    else:
        if depth == 0:
            best_move = random.choice(poss_moves)
            score = pos.sgn * count_material(pos.board)
        else:
            score = float("-inf") #want to maximise score
            random.shuffle(poss_moves) #o avoid threefold repetition
            for move in poss_moves:
                pos_copy = copy.deepcopy(pos)
                pos_copy.make_move(move)
                t = -1 * tree_search(pos_copy,depth-1,alpha = -1*beta,beta = -1*alpha)[1]
                if t > score:
                    score = t
                    best_move = move
                if score >= beta:
                    return best_move,score
                alpha = max(alpha,score)
    #print "best_move=",best_move
    #print "score=",score
    #print "\n"
    return best_move, score

def play_game(num_moves,white,black,verbose=True,depth=2):
    """if white/black = random, computer makes random choice
    if white/black = heuristic, computer uses heuristic
    if white/black = human, computer expects human player to make inputs
    maximum number of moves is num_moves. returns outcome of game as points for white
    depth is the search depth of the heuristic"""
    
    pos = Position(initial_board[:],in_check = False,move_seq=[])
    while pos.num <= num_moves:
        if verbose:
            print "\n"
            print "Turn =",pos.turn, "Move number =", pos.num
            pos.print_board2()
            print "in check?", pos.in_check
        
        outcome, reason, possible_moves, fifty_move_counter = evaluate_pos(pos)
        if outcome != None:
            if outcome == 1:
                print "White wins due to",reason
            elif outcome == 0:
                print "Black wins due to",reason
            else:
                print "Draw due to",reason
            return outcome        
                
        if (pos.turn == "white" and white == "random") or (pos.turn == "black" and black == "random"):
            choice = random.choice(possible_moves)
        
        elif (pos.turn == "white" and white == "heuristic") or (pos.turn == "black" and black == "heuristic"):     
            choice, evaluation = tree_search(pos,depth,outcome = outcome, poss_moves = possible_moves)
            #print "choice = ",choice
            #print "evaluation = ", evaluation          
        else:
            valid = False
            while not valid: 
                m = input("make move ").split(",") #input move as a string in the form: "e2,e4" or "d7,d8,Q"
                #convert start and finish square to internal representation
                start_col = col_dict_[m[0][0]]
                start_sq = (int(m[0][1]) + 1) * 10 + start_col
                finish_col = col_dict_[m[1][0]]
                finish_sq = (int(m[1][1]) + 1) * 10 + finish_col
                choice = (start_sq,finish_sq,piece_dict_[m[2]]) if len(m) > 2 else (start_sq,finish_sq)
                print choice
                if choice in possible_moves:
                    valid = True
                else:
                    print "invalid move"
        pos.make_move(choice)
        if verbose:
            print "choice = ",printable_move(choice)
    if pos.num > num_moves:
        print "move limit reached"
        return None
    if verbose:
            seq_string = "All moves"
            i = 1
            for move in pos.move_seq:
                seq_string += (" " + str(i) + "." + printable_move(move))
                i += 1
            print seq_string

def setup_position(pos):
    """sets up an arbitrary board position based on user inputs and checks legality.
    if pos is None, piece-by-piece user input, otherwise list of two strings of the form
    ['Pa2,Pb2,Ra1','Pa7,Ke8'] is expected."""
    
    board = [0]*120 #empty chess board
    
    edges = range(20)
    edges += range(100,120)
    edges += [10 * n for n in range(2,10)]
    edges += [10 * n + 9 for n in range(2,10)]
    #print edges
    
    for i in edges:
        board[i] = 100
    
    if pos == None:   
        #fill with white pieces 
        #user inputs in the form: "Ke4". If stop, enter "stop"    
        print "Enter white pieces\n"
        while True:
            try:
                p = input("Enter white piece ")
                if p == "stop":
                    break
                piece,col,row = list(p)
                piece = piece_dict_[piece]
                col = col_dict_[col]
                square = (int(row) + 1) * 10 + col
                board[square] = piece
            except:
                print "bad input"
                
        #fill with black pieces     
        #user inputs in the form: "Ke4". If stop, enter "stop"    
        print "Enter black pieces\n"
        while True:
            try:
                p = input("Enter black piece ")
                if p == "stop":
                    break
                piece,col,row = list(p)
                piece = -1 * piece_dict_[piece]
                col = col_dict_[col]
                square = (int(row) + 1) * 10 + col
                board[square] = piece
            except:
                print "bad input"
    else:
        white = pos[0].split(",")
        black = pos[1].split(",")
        for w in white:
            piece,col,row = list(w)
            piece = piece_dict_[piece]
            col = col_dict_[col]
            square = (int(row) + 1) * 10 + col
            board[square] = piece
        for b in black:
            piece,col,row = list(b)
            piece = -1 * piece_dict_[piece]
            col = col_dict_[col]
            square = (int(row) + 1) * 10 + col
            board[square] = piece
                      
    #check for legality
    
    #both sides have exactly one king"
    assert board.count(6) == 1 and board.count(-6) == 1
    #no pawns in first or last row
    assert not any(board[i] in (-1,1) for i in range(21,29)+range(91,99))    
    
    return board

def count_material(board):
    """returns material difference on board for white and black, using values in value_dict"""
    white_material = 0
    black_material = 0
    for square in on_board:
        if board[square] > 0:
            white_material += value_dict[board[square]]
        elif board[square] < 0:
            black_material += value_dict[abs(board[square])]
    return white_material - black_material

def test_suite():
    """tests play_game function"""
    
    #list of possible moves is correct
    #starting position is correct
    position = Position(board = initial_board[:])
    expected = set([(31,41),(31,51),(32,42),(32,52),(33,43),(33,53),(34,44),(34,54),(35,45),\
    (35,55),(36,46),(36,56),(37,47),(37,57),(38,48),(38,58),(22,41),(22,43),(27,46),(27,48)])
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 6, 0, 0, 4, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 3, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, -1, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63)]
    position = Position(board = board,turn = "white",move_seq = move_seq)
    position.print_board2()
    expected = set([(21, 22), (24, 35), (25, 26), (25, 35), (25, 27), (28, 27), (28, 26), (31, 41), (31, 51), (32, 42), (32, 52), (34, 44), (34, 54), (37, 47), (37, 57), (38, 48), (38, 58), (43, 64), (43, 62), (43, 51), (43, 22), (43, 35), (46, 67), (46, 65), (46, 54), (46, 58), (46, 27), (53, 64), (53, 75), (53, 86), (53, 42), (53, 62), (53, 71), (53, 44), (53, 35), (53, 26)])
    print "from generator"
    generated = set(position.make_move_list())
    seq_string = "Moves"
    i = 1
    for move in generated:
        seq_string += (" " + str(i) + "." + printable_move(move))
        i += 1
    print seq_string
    print "expected"
    seq_string = "Moves"
    i = 1
    for move in expected:
        seq_string += (" " + str(i) + "." + printable_move(move))
        i += 1
    print seq_string
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 6, 0, 0, 4, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 0, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, 3, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]    
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63), (53, 86)]
    position = Position(board = board,turn = "black",move_seq = move_seq)
    position.print_board2()
    expected = set([(95, 85), (95, 86), (95, 96)])
    print "from generator"
    generated = set(position.make_move_list())
    seq_string = "Moves"
    i = 1
    for move in generated:
        seq_string += (" " + str(i) + "." + printable_move(move))
        i += 1
    print seq_string
    print "expected"
    seq_string = "Moves"
    i = 1
    for move in expected:
        seq_string += (" " + str(i) + "." + printable_move(move))
        i += 1
    print seq_string
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 4, 0, 6, 0, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 0, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, 0, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63), (53, 86), (95, 86), (25, 27), (86, 95), (26, 25)]
    position = Position(board = board,turn = "black",move_seq = move_seq)
    expected = set([(63, 74), (63, 85), (63, 96), (63, 52), (63, 41), (63, 72), (63, 54), (63, 45), (63, 36), (73, 92), (73, 85), (73, 52), (73, 54), (73, 61), (76, 97), (76, 55), (76, 57), (76, 68), (76, 64), (81, 71), (81, 61), (82, 72), (82, 62), (84, 74), (84, 64), (87, 77), (87, 67), (88, 78), (88, 68), (91, 92), (94, 85), (95, 85), (95, 86), (95, 96), (98, 97), (98, 96)])
    assert set(position.make_move_list()) == expected

    board = setup_position(["Ke1,Ra1,Rh1,Nb3,Ng3,Pc2,Pd2,Pe5","Ke8,Bb4,Bf3,Qh4,Pd5"])
    move_seq = [(84,64)]
    position = Position(board = board,turn = "white",move_seq = move_seq)
    expected = set([(21, 31),(21, 41),(21, 51),(21, 61),(21, 71),(21, 81),(21, 91),(21, 22),(21, 23),(21, 24),(25, 26),(25, 36),(25, 27),(28, 38),(28, 48),(28, 58),(28, 27),(28, 26),(33, 43),(33, 53),(42, 63),(42, 61),(42, 54),(42, 23),(65, 75),(65, 74)])
    assert set(position.make_move_list()) == expected

    #checkmate and stalemate tests
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-5,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,turn = "white",move_seq = [])
    assert len(position.make_move_list()) == 0
    assert position.king_hanging(None) == True

    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-4,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,turn = "white",move_seq = [])
    assert len(position.make_move_list()) == 1
    assert position.king_hanging(None) == True
    
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-3,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,turn = "white",move_seq = [])
    assert len(position.make_move_list()) == 0
    assert position.king_hanging(None) == False
    
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-2,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,turn = "white",move_seq = [])
    assert len(position.make_move_list()) == 1
    assert position.king_hanging(None) == False
    
    #board setup and printing test
    new_board = setup_position(['Pa2,Pb2,Ra1,Ke1','Pa7,Ke8'])
    pos = Position(board = new_board)
    pos.print_board2()
      
    #error-free execution of lots of random games
    time0 = time.time()
    white_wins = 0
    black_wins = 0
    draws = 0
    undecided_games = 0
    total_games = 1000
    
    for count in range(total_games):
        outcome = play_game(500,"random","random",verbose = False)
        if outcome == 1:
            white_wins += 1
        elif outcome == 0:
            black_wins += 1
        elif outcome == 0.5:
            draws += 1
        else:
            undecided_games += 1
    time1 = time.time()
    print "total time elapsed = ",time1-time0,"seconds"
    
    #reasonable execution time
    assert 1.0 * (time1 - time0)/total_games < 1
    
    ##reasonable game outcomes
    white_percentage = 1.0 * (white_wins + 0.5 * draws) / (white_wins + black_wins + draws)
    print white_percentage
    #assert 0.3 <= white_percentage <= 0.7
    #assert 1.0 * undecided_games/total_games < 0.2
    #assert 1.0 * draws/total_games > 0.5
    
    #test heuristic function
    time0 = time.time()
    white_wins = 0
    black_wins = 0
    draws = 0
    undecided_games = 0
    total_games = 100
    for count in range(total_games):
        outcome = play_game(500,"random","heuristic",verbose = False, depth = 0)
        if outcome == 1:
            white_wins += 1
        elif outcome == 0:
            black_wins += 1
        elif outcome == 0.5:
            draws += 1
        else:
            undecided_games += 1
    time1 = time.time()
    print "total time elapsed = ",time1-time0,"seconds"

    white_percentage = 1.0 * (white_wins + 0.5 * draws) / (white_wins + black_wins + draws)
    print "heuristic average score", white_percentage
    

        
#play_game(200,'random','random',verbose = True)
cProfile.run("test_suite()")

#other simple heuristics: piece activation, central control, king safety
