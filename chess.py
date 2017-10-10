# -*- coding: utf-8 -*-
"""Chess program that either accepts human player's input moves or 
randomly selects moves"""

import random, copy, time, cProfile, functools

def decorator(d):
    "Make function d a decorator: d wraps a function fn."
    def _d(fn):
        return functools.update_wrapper(d(fn), fn)
    return _d
decorator = decorator(decorator)

@decorator
def memo(f):
    """Decorator that caches the return value for each call to f(args).
    Then when called again with same args, we can just look it up."""
    cache = {}
    def _f(*args):
        try:
            return cache[args]
        except KeyError:
            result = f(*args)
            cache[args] = result
            return result
        except TypeError:
            # some element of args can't be a dict key
            return f(*args)
    _f.cache = cache
    return _f

not_on_board = [10*i for i in range(2,10)] + [10*i+9 for i in range(2,10)]
on_board = [square for square in range(20,100) if square not in not_on_board]

col_dict = {1: "a", 2: "b", 3: "c", 4: "d", 5: "e", 6: "f", 7: "g", 8: "h"}
col_dict_ = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6, "g": 7, "h": 8}
piece_dict = {1: "P", 2: "N", 3: "B", 4: "R", 5: "Q", 6: "K"}
piece_dict_ = {"P": 1, "N": 2, "B": 3, "R": 4, "Q": 5, "K": 6}

#maps piece representations to values
value_dict = {1: 1, 2: 3, 3: 3, 4: 5, 5: 9, 6: 99999}

uni_pieces = {'bR':'♜', 'bN':'♞', 'bB':'♝', 'bQ':'♛', 'bK':'♚', 'bP':'♟',
                  'wR':'♖', 'wN':'♘', 'wB':'♗', 'wQ':'♕', 'wK':'♔', 'wP':'♙', '  ':'  '}
                  
table = None

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

initial_board = tuple(initialise_board())

def print_board3(board):
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
            line += d[board[k]]
            line += " |"
        print line
    print "   a   b   c   d   e   f   g   h"


class Position(object):
    """A chess position complete with history"""
    def __init__(self,board = initial_board,sgn = 1,move_seq = (),\
                num_pieces = 32,old_num_pieces = None,pawn_moved = None,fifty_move_counter = 0,\
                in_check = None,castling = False,num = 1, wc = (False,False), bc = (True,True), ep = None):
        global ht
        
        self.board = list(board)
        self.sgn = sgn
        self.move_seq = list(move_seq)
        self.num = num
        self.num_pieces = num_pieces
        self.old_num_pieces = old_num_pieces
        self.pawn_moved = pawn_moved #was the last move a pawn move?
        self.fifty_move_counter = fifty_move_counter
        self.in_check = in_check #is current player in check?
        self.castling = castling #was last move castling move?
        self.history = [self.board[:]]
        self.fmh = [self.fifty_move_counter]
        
        self.wc = wc #default args wc and bc need to be immutable
        self.bc = bc
        self.wch = [self.wc]
        self.bch = [self.bc]
        self.ep = ep
        self.eph = [self.ep]
        
        ht = dict()
        zobrist_init()
        h = zobrist_hash(self)
        ht["ordered"] = [h]
        ht[h] = {"moves": [0]}
        
    
    #make rollback method: just keep track of past board positions, infer other attributes from there
    
    def rollback(self,depth):
        """reverts to previous board position. depth = 1 corresponds to directly previous one"""
        
        #print "rollback depth=",depth
        #print "before rollback:"
        #self.print_board2()
        #print "move_seq=",self.move_seq
        #print "before rollback board history"
        #for b in self.history:
        #    print_board3(b)
        #    print "\n"
        #print "self.fmh=",self.fmh
        self.board = self.history[-1-depth]
        self.sgn *= (-1)**depth 
        self.move_seq = self.move_seq[:-depth]
        #print "updated move_seq=",self.move_seq
        self.num -= depth
        
        ht["ordered"] = ht["ordered"][:-depth]
        
        self.num_pieces = sum(1 if self.board[square] != 0 else 0 for square in on_board)
        self.old_num_pieces = sum(1 if self.history[-1-depth][square] != 0 else 0 for square in on_board)
        self.pawn_moved = abs(self.move_seq[-depth][0]) == 1 if len(self.move_seq) > 0 else False    
        self.fifty_move_counter = self.fmh[-1 - depth]
        self.in_check = None #maybe change
        if len(self.move_seq) > 0:
            self.castling = abs(self.board[self.move_seq[-depth][0]]) == 6 and abs(self.move_seq[-depth][1]-self.move_seq[-depth][0]) == 2
        else:
            self.castling = False
        #just need to keep track of history from tree search onwards -> speedup?
        new = []
        for i in range(len(self.history)-1):
            new.append(self.history[i][:])
            #for i in range(depth):
            #    del self.history[-1]
        self.history = new 
        self.fmh = self.fmh[:-depth]
        self.wc = self.wch[-1-depth]
        self.bc = self.bch[-1-depth]
        
        self.wch = self.wch[:-depth]
        self.bch = self.bch[:-depth]

        self.ep = self.eph[-1-depth]
        self.eph = self.eph[:-depth]
        
        #print "after_rollback"
        #self.print_board2()
        #print "after rollback board history"
        #for b in self.history:
        #    print_board3(b)
        #    print "\n"
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 
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
                line += uni_pieces[d[self.board[k]]]
                line += " |"
            print line
        print "   a   b   c   d   e   f   g   h"
        
        
    def make_move(self,move,verbose = False, update_in_check = True, just_board = False):
        """execute a move on the board"""
        global ht
        if move is not None:          
            castling = True if abs(self.board[move[0]]) == 6 and abs(move[1]-move[0]) == 2 else False           
            if not just_board:
                update_hash(self,ht["ordered"][-1],move)
                
                #will other player be in check?                
                if update_in_check:
                    self.in_check = self.check_check(move,castling)
                
                self.move_seq.append(move)
                if verbose:
                    print "Move =", printable_moves(move)
                    #print move_seq
                
                self.castling = castling
                
                #50 move rule: updating counter if no pawn has moved and a piece has not been captured 
                self.pawn_moved = abs(self.board[move[0]]) == 1
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
            
            if self.num_pieces == self.old_num_pieces and not self.pawn_moved:
                self.fifty_move_counter += 1
            else:
                self.fifty_move_counter = 0
            self.fmh.append(self.fifty_move_counter)
                      
            if verbose:
                #print board
                self.print_board2(self.board)
            self.num += 1
            if verbose:
                print "\n"
            self.history.append(self.board[:])
                               
        self.sgn = 1 if self.sgn == -1 else -1
        #if not just_board:
        #    print self.num
        #    print "wc =",self.wc
        #    print "bc =",self.bc

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
            #print "calc_offsets with king"
            #print "with_castling =",with_castling
            #print "sgn =",self.sgn, "wc =",self.wc,"bc =",self.bc
            if with_castling:               
                if self.sgn == 1:
                    if self.wc[0] == True:
                        offsets.append(2)
                    if self.wc[1] == True:
                        offsets.append(-2)
                else:
                    if self.bc[0] == True:
                        offsets.append(2)
                    if self.bc[1] == True:
                        offsets.append(-2) 
            #print "offsets =",offsets             
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
            elif len(self.move_seq) > 0:
                if (pos in range(c,d) and self.move_seq[-1] == (pos+piece_sgn*19,pos-piece_sgn) and self.board[pos-piece_sgn] == -1*piece_sgn): #pawn to the left
                    offsets.append(piece_sgn*9)
            #topright or bottomleft
            if piece_sgn * self.board[pos + piece_sgn*11] < 0:
                offsets.append(piece_sgn*11) 
            elif len(self.move_seq) > 0:
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

    def is_attacked(self,square,di = None,smallest = False,p = None):
        """returns True if square is attacked by player whose turn it is"""
        #check whether there are pawns diagonally opposite or knights an L-offset away or king adjacent
        #then check along rows/columns (rooks, queens) and diagonals (bishops, queens) until hit a piece
        #print "calling is_attacked with square =",square
        if smallest: 
            attacking_pieces = []
            
        for offset in [-9*self.sgn,-11*self.sgn]: #check pawns
            new_sq = square+offset
            if self.board[new_sq] == self.sgn:
                if not smallest:
                    return True
                if smallest and ((new_sq,square) in p or (new_sq,square,2) in p\
                or (new_sq,square,3) in p or (new_sq,square,4) in p or (new_sq,square,5) in p):
                    return True, (1,new_sq)
                
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
                if not smallest:
                    return True 
                if smallest and (new_sq,square) in p:
                    return True, (2,new_sq)
                
        #check rows (rooks and queens) and diagonals (bishops and queens)
        for a,b,c in [("d1",9,3),("d2",11,3),("d3",1,4),("d4",10,4)]:
            if di is None or di == "d0" or di == a:
                for direction in [b,-b]: 
                    new_sq = square + direction
                    while new_sq in on_board:
                        if self.board[new_sq] in (c*self.sgn,5*self.sgn):
                            if not smallest:
                                return True
                            if smallest and (new_sq,square) in p:
                                attacking_pieces.append((abs(self.board[new_sq]),new_sq))
                                break
                            else:
                                new_sq += direction
                        elif self.board[new_sq] != 0:
                            break
                        else:
                            new_sq += direction
                if di == a: return False
     
        for offset in [-11,-10,-9,-1,1,9,10,11]: #check king
            new_sq = square + offset
            if self.board[new_sq] == 6*self.sgn:
                if not smallest:
                    return True
                if smallest and (new_sq,square) in p:
                    attacking_pieces.append((abs(self.board[new_sq]),new_sq))
                    break
                
        if smallest:
            m = min(attacking_pieces, key = lambda i: i[0]) if len(attacking_pieces) > 0 else None 
            return (m is not None), m
        #if no flag is raised
        return False   

    def king_hanging(self,move):
        """checks whether, after colour's move, colour's king can be captured in a given 
        position by the other player."""
        #print "calling king_hanging with move=", printable_moves(move)
        if move == None and self.in_check == True:
            return True
        if move == None or self.in_check != False: #in_check might be unknown
            old_board = self.board[:]
            self.make_move(move,update_in_check = False,just_board = True) #avoid infinite recursion
            kings_square = self.board.index(self.sgn* -6)
            a = self.is_attacked(kings_square)
            self.board = old_board[:]
            self.sgn = 1 if self.sgn == -1 else -1
            #print "1st case", a
            return a
        kings_square = self.board.index(self.sgn*6)
        col_diff = move[0] % 10 - kings_square % 10
        row_diff = move[0]/10 - kings_square/10
        
        di=None
        if abs(self.board[move[0]]) == 6:
            di="d0"
        elif col_diff == -row_diff:
            di="d1" 
        elif col_diff == row_diff:
            di="d2"
        elif col_diff == 0:
            di="d4"
        elif move[0]/10 == kings_square/10:
            di="d3"    
        if di is not None: #piece might have been pinned
            old_board = self.board[:]
            self.make_move(move,update_in_check = False,just_board = True) #avoid infinite recursion
            kings_square = self.board.index(self.sgn* -6)
            #print kings_square
            a = self.is_attacked(kings_square,di)
            self.board = old_board[:]
            self.sgn = 1 if self.sgn == -1 else -1
            #print "2nd case", a
            #if a: print "move =",printable_moves(move)," kings_square =",kings_square
            return a
        #print "3rd case", False
        return False
    
    def check_check(self,move,castling):
        """determines whether move puts other player in check. castling indicates whether move is a castling move"""
     
        opp_king_sq = self.board.index(-6*self.sgn)
        #self.print_board2()
        #print "examining", printable_moves(move)
        #print printable_moves(self.move_seq)
        #print "check_check failing"
        #opp_king_sq = self.board.index(-6*self.sgn)
        old_board = self.board[:]
        self.make_move(move,update_in_check = False,just_board = True)
        
        #print "move end=",move[1]
        #print "opp_king_sq=",opp_king_sq
        #print "piece on new sq?", position_copy.board[move[1]]
    
        def rollback():
            self.board = old_board[:]
            self.sgn = 1 if self.sgn == -1 else -1
        
        if self.attacks(move[1],opp_king_sq): #if moved piece attacks opposite king, return True (includes pawn promotion case)
            #print "moved piece attacks opp king"
            rollback()
            return True
        
        #if discovery possible, check pieces on row/col/diagonal. also check castling  
        diff = opp_king_sq - move[0]
        col_diff = opp_king_sq % 10 - move[0] % 10
        row_diff = opp_king_sq/10 - move[0]/10                                     
        
        check_castling = True
        for a,b,c,d in (
        (col_diff == -row_diff,row_diff > 0,9,3),
        (col_diff == row_diff,col_diff > 0,11,3),
        (col_diff == 0,diff > 0,10,4),
        (row_diff == 0,diff > 0,1,4)):
            if a:
                check_castling = False
                direction = -c if b else c
                new_sq = move[0] + direction
                while new_sq in on_board:
                    if self.board[new_sq] in (-d*self.sgn,-5*self.sgn):
                        rollback()
                        return True
                    elif self.board[new_sq] != 0:
                        break
                    else:
                        new_sq += direction
                break                                                                        

        if check_castling:
            if self.sgn == -1:
                if move[1] == 27: #kingside castling, so rook on f1
                    if self.attacks(26,opp_king_sq):
                        rollback()
                        return True
                else: #queenside castling, so rook on d1
                    if self.attacks(24,opp_king_sq):
                        rollback()
                        return True
            else:
                if move[1] == 97: #kingside castling, so rook on f8
                    if self.attacks(96,opp_king_sq):
                        rollback()
                        return True
                else: #queenside castling, so rook on d8
                    if self.attacks(94,opp_king_sq):
                        rollback()
                        return True
        rollback()
        return False
        
    def make_move_list(self,check_for_king_hanging = True, with_castling = True):
        """list legal moves in a given position in the form: (old field,new field)
        for white: colour = "white", for black: colour = "black"
        need to be able to exclude castling moves so as to avoid 
        infinite recursion when checking whether castling puts the king in check 
        (opponent's castling needn't be considered as a response to determine 
        whether king is in check after castling)"""
        global mml_calls, mml_hash_returns
        if check_for_king_hanging and with_castling:
            mml_calls += 1
        if check_for_king_hanging and with_castling and "move_list" in ht[ht["ordered"][-1]]:
            #print "looked up move_list"
            mml_hash_returns += 1
            return ht[ht["ordered"][-1]]["move_list"] 
       
        move_list = []
        #print "calling make_move_list, colour=",colour,"check_for_king_hanging=",check_for_king_hanging
        
        pairs = ((pair[0],abs(pair[1])) for pair in enumerate(self.board) if pair[0] in on_board and self.sgn*pair[1] > 0)
        for pos, piece in pairs:
            offsets = self.calc_offsets(piece,pos,with_castling = with_castling)
            potential_targets = [pos + offset for offset in offsets]
            potential_targets = [target for target in potential_targets if target in on_board]
            targets = (target for target in potential_targets if self.sgn*self.board[target] <= 0) if piece != 1 else potential_targets # pawns already checked
            #if pawn moves to last row (8th or 1st), promote to N/B/R/Q
            if piece == 1:
                for target in targets:
                    if target not in range(21,29)+range(91,99):
                        move_list.append((pos,target))
                    else:
                        for promoted_to in (2,3,4,5):
                            move_list.append((pos,target,promoted_to))
            else:
                for target in targets:
                    move_list.append((pos,target))
        #print "move_list =",printable_moves(move_list)        
        if check_for_king_hanging:
            for move in copy.copy(move_list):
                #if after move own king is in check, remove this move from the move list
                #print "checking whether king hanging after move=",move
                if self.king_hanging(move):
                    #print "\nremoved ",printable_moves(move)
                    move_list.remove(move)
        #if "move_list" in ht[ht["ordered"][-1]] and with_castling and check_for_king_hanging:
        #    try:
        #        assert set(ht[ht["ordered"][-1]]["move_list"]) == set(move_list)
        #    except:
        #        self.print_board2()                
        #        print "move_seq =",printable_moves(self.move_seq)
        #        print "self.wc =", self.wc
        #        #print "self.wch =",self.wch
        #        print "self.bc =", self.bc
        #        #print "self.bch =",self.bch
        #        print "move_list from make_move_list =",printable_moves(move_list)
        #        print "from ht ",printable_moves(ht[ht["ordered"][-1]]["move_list"])
        #        assert set(ht[ht["ordered"][-1]]["move_list"]) == set(move_list)
        if check_for_king_hanging and with_castling and "move_list" not in ht[ht["ordered"][-1]]:  
            ht[ht["ordered"][-1]]["move_list"] = move_list
        return move_list

def printable_moves(moves):
    """prints either a single move or a list of moves by converting internal 
    square representation to comon chess notation"""
    if moves is None:
        return ""
    if type(moves) not in (list,set):
        moves = [moves]
    if len(moves) == 0:
        return ""
    seq_string = "Moves"
    i = 1
    for move in moves:   
        start = move[0]
        finish = move[1]
        start_col = col_dict[start % 10]
        start_row = str(start/10-1)
        finish_col = col_dict[finish % 10]
        finish_row = str(finish/10 - 1)
        s = start_col + start_row + "-" + finish_col + finish_row
        if len(move) == 2:
            final = s
        else:
            promoted_to = move[2]
            final = s + piece_dict[abs(promoted_to)]
        seq_string += (" " + str(i) + "." + final)
        i += 1
    return seq_string if len(moves) > 1 else final

def evaluate_pos(pos,in_check = None):
    """checks for checkmate/stalemate/fifty-move rule/threefold repetition/insufficient material"""
    #print "in-check=",in_check
    reason = None
    outcome = None
    possible_moves = pos.make_move_list()
    #print "\ncan't determine possible_moves"
    #pos.print_board2()
    #print printable_moves(pos.move_seq)
    #print "castling =",pos.castling
    #possible_moves = pos.make_move_list()
           
    if len(possible_moves) == 0: #no possible moves
        #if in check, checkmate
        if pos.king_hanging(None):
            reason = "checkmate"
            outcome = 0 if pos.sgn == 1 else 1
        #else stalemate
        else:
            reason = "stalemate"
            outcome = 0.5
        
    #threefold repetition"
    #ignores possible hash collision. to deal with this, store list of historic
    #board positions and in the case of triple occurence of a hash value,
    #do another check of the full board positions
    elif len(ht[ht["ordered"][-1]]) == 3:
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
    elif pos.fifty_move_counter >= 100:
        reason = "50 move rule"
        outcome = 0.5

    return outcome, reason, possible_moves        

def see(pos,square,poss = None):
    #print "calling see"
    #pos.print_board2()
    #print "square=",square
    value = 0
    if poss is None:
        poss = pos.make_move_list()
     
    piece = pos.is_attacked(square,smallest = True,p = poss)[1]
    #print "piece=",piece
    #print "key=",abs(pos.board[square])
    if piece: 
        captured_value = value_dict[abs(pos.board[square])]
        #print "making move =",printable_moves((piece[1],square))
        pos.make_move((piece[1],square)) 
        #only if allowed to take! not if piece is king and sq is defended or if piece is moving out of pin
        value = max(0,captured_value - see(pos,square))
        #print "len(pos.history) =",len(pos.history)
        #print "move_seq =",pos.move_seq
        pos.rollback(1)
    return value

def quiesce(pos,alpha,beta,p = None,total_depth = 0,testing = False):
    global quiesce_calls
    if testing:
        quiesce_calls += 1      
    #print "sgn=",pos.sgn
    #print "alpha=",alpha
    #print "beta=",beta
    #print "total depth=",total_depth
    #pos.print_board2()
    val = pos.sgn*count_material(pos.board)
    #print "val=",val
    if val >= beta:
        return beta 
    alpha = max(alpha,val)
    #more practical to have is_capture, is_check,... attributes for each move
    moves = pos.make_move_list(with_castling = False) if p is None else p #really just need to list captures
    #print "possible moves =",printable_moves(moves)
    #list all possible captures that are not bad
    captures = []
    for move in moves:
        capture_value = abs(pos.board[move[1]])
        if capture_value > 0:
            #print printable_moves(move)
            pos.make_move(move)
            if capture_value >= see(pos,move[1]) or len(move) > 2: #ensure no bad capture (but allow for promotions)
                captures.append(move)
            pos.rollback(1)
    #print "captures =",printable_moves(captures)
    while len(captures) > 0:
        pos.make_move(captures[-1])
        score = -quiesce(pos,-beta,-alpha,total_depth = total_depth + 1,testing = testing)
        pos.rollback(1)
        del captures[-1]
        if score >= beta:
            return beta
        alpha = max(alpha,score)
    return alpha 

def tree_search(pos,depth,outcome = None, poss_moves = None, alpha = float("-inf"),beta = float("inf"),\
                total_depth = 0, testing = False, q = True):
    """evaluates all possible moves up to the depth and returns best one along with position evaluation"""
    global beta_cutoffs,ts_calls, quiesce_calls
    #pos.print_board2()
    #print "total_depth =",total_depth
    if testing:
        ts_calls += 1  
    
    if poss_moves == None:
        outcome, reason, poss_moves = evaluate_pos(pos)
    
    if testing:           
        if total_depth == 0:
            #count number of nodes that would be examined without alpha beta pruning   
            
            def enumerate_pos(pos,depth):
                if depth == 0:
                    return 1
                num_positions = 1        
                for move in poss_moves:
                    pos.make_move(move)
                    num_positions += enumerate_pos(pos,depth-1)
                    pos.rollback(1)
                return num_positions
            
            print "total number of nodes =",enumerate_pos(pos,depth),"depth =",depth
    
    #print "\n"
    #print "tree_search"
    #print "outcome=",outcome
    #print "poss_moves=",poss_moves
    #print "depth=",depth
    #print "last move " + printable_moves(move_seq[-1]) if len(move_seq) > 0 else "initial position"
    #pos.print_board2()      
                 
    best_move = None
    if outcome == 1:
        score = pos.sgn * 99999 #if this is inf, might not return any move if being checkmated is certain
    elif outcome == 0.5:
        score = 0
    elif outcome == 0:
        score = pos.sgn * -99999
    else:
        #print "number of moves =", len(pos.move_seq), "dept =", depth
        if depth == 0:
            if q:
                score = quiesce(pos,alpha,beta,poss_moves,testing = True)
            else:
                score = pos.sgn * count_material(pos.board)
                                  
            best_move = random.choice(poss_moves)
        else:
            score = float("-inf") #want to maximise score
            random.shuffle(poss_moves) #o avoid threefold repetition
            for move in poss_moves:
                #print printable_moves(move)
                #pos.print_board2()
                #old_wc = pos.wc
                #print "old_wc =",old_wc,"at depth =",depth
                #old_bc = pos.bc
                #print "old_bc =",old_bc
                pos.make_move(move)
                #print "after make_move","at depth =",depth
                #amm_wc = pos.wc
                #print "wc =",amm_wc
                #amm_bc = pos.bc
                #print "bc =",amm_bc                            
                t = -1 * tree_search(pos,depth-1,alpha = -1*beta,beta = -1*alpha,\
                                    total_depth = total_depth + 1,testing = testing,q = q)[1]
                if t > score:
                    score = t
                    best_move = move
                pos.rollback(1)
                #print "after rollback","at depth =",depth
                #print "wc =",pos.wc
                #print "bc =",pos.bc
                #assert old_wc == pos.wc
                #assert old_bc == pos.bc
                if score >= beta: #previous opponent's move is refuted
                    beta_cutoffs += 1
                    #print "beta-cutoff"
                    return best_move,score
                alpha = max(alpha,score)
    #print "best_move=",best_move
    #print "score=",score
    #print "\n"
    #pos.rollback(0)
    return best_move, score

def play_game(num_moves,white,black,verbose = True,depth1 = None,depth2 = None, testing = False):
    """if white/black = random, computer makes random choice
    if white/black = heuristic, computer uses heuristic
    if white/black = human, computer expects human player to make inputs
    maximum number of moves is num_moves. returns outcome of game as points for white
    depth1 is the search depth of the first heuristic, depth 2 of the second (if present)"""
    
    global ts_calls, quiesce_calls, ht
    
    pos = Position()
    
    while pos.num <= num_moves:
        if verbose:
            print "\n"
            turn = "white" if pos.sgn == 1 else "black"
            print "Turn =",turn, "Move number =", pos.num
            pos.print_board2()
            #print "in check?", pos.in_check
        
        outcome, reason, possible_moves = evaluate_pos(pos)
        if outcome != None:
            if outcome == 1:
                print "White wins due to",reason
            elif outcome == 0:
                print "Black wins due to",reason
            else:
                print "Draw due to",reason
            return outcome        
                
        if (pos.sgn == 1 and white == "random") or (pos.sgn == -1 and black == "random"):
            choice = random.choice(possible_moves)
        
        elif pos.sgn == 1 and white == "heuristic":     
            choice, evaluation = tree_search(pos,depth1,outcome = outcome, poss_moves = possible_moves, testing = testing,q=True)
            if testing:
                print "ts_calls =",ts_calls
                print "quiesce_calls =",quiesce_calls
                ts_calls = 0
                quiesce_calls = 0
        elif pos.sgn == -1 and black == "heuristic":
            choice, evaluation = tree_search(pos,depth2,outcome = outcome, poss_moves = possible_moves, testing = testing,q=False)
            if testing:
                print "ts_calls =",ts_calls
                print "quiesce_calls =",quiesce_calls
                ts_calls = 0
                quiesce_calls = 0
            #print "choice = ",choice
            #print "evaluation = ", evaluation          
        else:
            valid = False
            while not valid: 
                while True:
                    m = input("make move ") #input move as a string in the form: "e2,e4" or "d7,d8,Q"
                    if m == "takeback":
                        pos.rollback(2)
                        pos.print_board2()
                    else:
                        m = m.split(",")
                        break
                #convert start and finish square to internal representation
                start_col = col_dict_[m[0][0]]
                start_sq = (int(m[0][1]) + 1) * 10 + start_col
                finish_col = col_dict_[m[1][0]]
                finish_sq = (int(m[1][1]) + 1) * 10 + finish_col
                choice = (start_sq,finish_sq,piece_dict_[m[2]]) if len(m) > 2 else (start_sq,finish_sq)
                #print choice
                if choice in possible_moves:
                    valid = True
                else:
                    print "invalid move"
        pos.make_move(choice)
        if verbose:
            print "choice = ",printable_moves(choice)
    if pos.num > num_moves:
        print "move limit reached"
        return None
    if verbose:
            seq_string = "All moves"
            i = 1
            for move in pos.move_seq:
                seq_string += (" " + str(i) + "." + printable_moves(move))
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

def perft(pos,depth):
    """recursively enumerates all leaf nodes in game tree up to depth. terminal nodes are not counted if they are not at depth "depth"."""
    #ensure perft ignores threefold repetition, 50-move-rule and insufficient material
    nodes = 0
    if depth == 0:
        return 1
    moves = pos.make_move_list()
    for i in range(len(moves)):
        pos.make_move(moves[i])
        nodes += perft(pos,depth - 1)
        pos.rollback(1)
    return nodes
    
def zobrist_init():
    """fill a table of random bitstrings"""
    
    global table
    table = [0]*77
    #indices 0-63 of table hold piece-square pairs, 64 is for black to move, 65-68 for castling rights, 69-76 for e.p. column
    for i in range(64): 
        table[i] = [0]*12
        for j in range(12):
            s = ""
            for k in range(64):
                s += str(random.randint(0,1))
            table[i][j] = s
    for i in range(64,77):
        s = ""
        for k in range(64):
            s += str(random.randint(0,1))
        table[i] = s
    return table


def xor(a,b):
    c = ""
    #print "a=",a
    #print "b=",b
    #assert len(a) == len(b)
    for i in range(len(a)):
        if a[i] != b[i]:
            c += "1"
        else:
            c += "0"
    return c
    
def zobrist_hash(pos):
    global table
    
    h = '0'*64
    #square-piece pairs
    for i in range(len(on_board)):
        if pos.board[on_board[i]] != 0:
            j = pos.board[on_board[i]]
            if j < 0:
                j += 6
            else:
                j += 5
                
            #print i
            #print j
            h = xor(h,table[i][j])
    #black to move
    if pos.sgn == -1:
        h = xor(h,table[65])
    #castling rights
    if pos.wc[0]:#white kingside
        h = xor(h,table[66])
    if pos.wc[1]:#white queenside
        h = xor(h,table[67])
    if pos.bc[0]:#black kingside
        h = xor(h,table[68])
    if pos.bc[1]:#black queenside
        h = xor(h,table[69])
    #en passant column
    if pos.ep is not None: #pos.ep indicate e.p. column (where pawn has just made a double-step)
        h = xor(h,table[69 + pos.ep])
        
    return h

def update_hash(pos,h,move):
    global ht
    
    start_sq = on_board.index(move[0])
    start_piece = pos.board[move[0]] + 6 if pos.board[move[0]] < 0 else pos.board[move[0]] + 5
    
    target_sq = on_board.index(move[1])
    h = xor(h,table[start_sq][start_piece]) #piece not on start square
    
    if len(move) == 2:    
        h = xor(h,table[target_sq][start_piece]) #piece on target square
    else: #if promotion
        promoted_to = move[2] * -1 + 5 if pos.board[move[0]] < 0 else move[2] + 6
        h = xor(h,table[target_sq][promoted_to]) 
    if pos.board[move[1]]:
        target_piece = pos.board[move[1]] + 5 if pos.board[move[1]] < 0 else pos.board[move[1]] + 6
        h = xor(h,table[target_sq][target_piece]) #captured piece not on target square
    
    #castling
    if pos.board[move[0]] == 6:
        if move[1] - move[0] == 2: #white kingside
            h = xor(h,table[7][4]) #rook no longer on h1
            h = xor(h,table[5][4]) #rook on f1
        elif move[1] - move[0] == -2: #white queenside
            h = xor(h,table[0][4]) #rook no longer on a1
            h = xor(h,table[3][4]) #rook on d1
    elif pos.board[move[0]] == -6:
        if move[1] - move[0] == 2: #black kingside
            h = xor(h,table[63][2]) #rook no longer on h8
            h = xor(h,table[61][2]) #rook on f8
        elif move[1] - move[0] == -2: #black queenside
            h = xor(h,table[56][2]) #rook no longer on a8
            h = xor(h,table[59][2]) #rook on d8

    #en passant
    elif pos.board[move[0]] == 1:
        if not pos.board[move[1]]: 
            if move[1] - move[0] == 9: #white takes e.p. up-left
                h = xor(h,table[start_sq - 1][5]) #black pawn to the left of start_sq is gone
            elif move[1] - move[0] == 11: #white takes e.p. up-right
                h = xor(h,table[start_sq + 1][5]) #black pawn to the right of start_sq is gone
    elif pos.board[move[0]] == -1:
        if not pos.board[move[1]]: 
            if move[1] - move[0] == -9: #black takes e.p. down-right
                h = xor(h,table[start_sq + 1][6]) #white pawn to the right of start_sq is gone
            elif move[1] - move[0] == -11: #black takes e.p. down-left
                h = xor(h,table[start_sq - 1][6]) #white pawn to the left of start_sq is gone
                 
    #other side to move
    h = xor(h,table[64])
    
    #castling rights
    
    old_wc = pos.wc[:]
    old_bc = pos.bc[:]
    
    #print pos.sgn
    if pos.sgn == 1:
        pos.bc = (False,False)
    else:
        pos.wc = (False,False)
    sq = 95 if pos.sgn == 1 else 25 #if black just moved then update white's castling rights or vice-versa
    #check that king has not moved, rook has not moved, rook is still there,\
    #all squares inbetween are empty, king is not in check
    c = abs(pos.board[move[0]]) == 6 and abs(move[1]-move[0]) == 2
    starts = [m[0] for m in pos.move_seq]
    if sq not in starts and not pos.check_check(move,c):
        ks = False
        #kingside castling
        if sq + 3 not in starts and abs(pos.board[sq+3]) == 4 and pos.board[sq+1] == 0 and pos.board[sq+2] == 0:
        #check that king wouldn't castle over attacked square
            
            old_board = pos.board[:]
            pos.make_move(move,update_in_check = False,just_board = True)
     
            if not pos.king_hanging((sq,sq+1)) and not pos.king_hanging((sq,sq+2)):
                ks = True       
            pos.sgn = 1 if pos.sgn == -1 else -1
            pos.board = old_board[:]
        
        qs = False
        #queenside castling
        if sq - 4 not in starts and abs(pos.board[sq-4]) == 4 and pos.board[sq-1] == 0 and pos.board[sq-2] == 0 and pos.board[sq-3] == 0:              
            #check that king wouldn't castle over attacked square
            
            old_board = pos.board[:]
            pos.make_move(move,update_in_check = False,just_board = True)
            
            if not pos.king_hanging((sq,sq-1)) and not pos.king_hanging((sq,sq-2)):
                #add castling to offsets
                qs = True
            pos.sgn = 1 if pos.sgn == -1 else -1 
            pos.board = old_board[:]
            if sq == 25:
                pos.wc = (ks,qs)
            else:
                pos.bc = (ks,qs)
                   
    #if other side made a null move, could player castle?  just do an 
    #in-principle update indicating whether rook or king have already moved. then do full update when sgn changes
    if pos.sgn == 1:
        king_sq = 25
        rook_sqs = (28,21)
    else:
        king_sq = 95
        rook_sqs = (98,91)    
    if king_sq != move[0] and king_sq not in starts:
        ks = rook_sqs[0] != move[0] and rook_sqs[0] not in starts
        qs = rook_sqs[1] != move[0] and rook_sqs[1] not in starts
        if pos.sgn == 1:
            pos.wc = (ks,qs)
        else:
            pos.bc = (ks,qs)
    pos.wch.append(pos.wc)
    pos.bch.append(pos.bc)
    
    if pos.wc[0] != old_wc[0]:#white kingside
        h = xor(h,table[65])
    if pos.wc[1] != old_wc[1]:#white queenside
        h = xor(h,table[66])
    if pos.bc[0] != old_bc[0]:#black kingside
        h = xor(h,table[67])
    if pos.bc[1] != old_bc[1]:#black queenside
        h = xor(h,table[68])        
                                                           
    #ep column
    old_ep = pos.ep
    #print abs(pos.board[move[0]]) == 1
    #print abs(move[1] - move[0]) == 20
    #print -pos.sgn
    #print -pos.sgn in (pos.board[move[1] - 1],pos.board[move[1] + 1])
    if abs(pos.board[move[0]]) == 1 and abs(move[1] - move[0]) == 20\
        and -pos.sgn in (pos.board[move[1] - 1],pos.board[move[1] + 1]):
        pos.ep = move[0] % 10
    else:
        pos.ep = None
    if old_ep != pos.ep:
        if old_ep is not None:
            h = xor(h,table[68 + old_ep]) #xor out old pos.ep
        if pos.ep is not None:
            h = xor(h,table[68 + pos.ep]) #xor in new pos.ep
    pos.eph.append(pos.ep)        
    ht["ordered"].append(h)
    if h in ht:
        ht[h]["moves"].append(pos.num + 1)
    else:
        ht[h] = {"moves": [pos.num + 1]}
    return h

def test_suite():
    """tests play_game function"""
    
    #list of possible moves is correct
    #starting position is correct
    print "testing move lists"
    
    position = Position()
    position.print_board2()
    expected = set([(31,41),(31,51),(32,42),(32,52),(33,43),(33,53),(34,44),(34,54),(35,45),\
    (35,55),(36,46),(36,56),(37,47),(37,57),(38,48),(38,58),(22,41),(22,43),(27,46),(27,48)])
    print "from generator"
    generated = set(position.make_move_list())
    print printable_moves(generated)
    print "expected"
    print printable_moves(expected)
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 6, 0, 0, 4, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 3, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, -1, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63)]
    position = Position(board = board,sgn = 1,move_seq = move_seq, wc = [True,False],bc = [True,True])
    position.print_board2()
    expected = set([(21, 22), (24, 35), (25, 26), (25, 35), (25, 27), (28, 27), (28, 26), (31, 41), (31, 51), (32, 42), (32, 52), (34, 44), (34, 54), (37, 47), (37, 57), (38, 48), (38, 58), (43, 64), (43, 62), (43, 51), (43, 22), (43, 35), (46, 67), (46, 65), (46, 54), (46, 58), (46, 27), (53, 64), (53, 75), (53, 86), (53, 42), (53, 62), (53, 71), (53, 44), (53, 35), (53, 26)])
    print "from generator"
    generated = set(position.make_move_list())
    print printable_moves(generated)
    print "expected"
    print printable_moves(expected)
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 6, 0, 0, 4, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 0, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, 3, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]    
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63), (53, 86)]
    position = Position(board = board,sgn = -1,move_seq = move_seq)
    position.print_board2()
    expected = set([(95, 85), (95, 86), (95, 96)])
    print "from generator"
    generated = set(position.make_move_list())
    print printable_moves(generated)
    print "expected"
    print printable_moves(expected)
    assert set(position.make_move_list()) == expected
    
    board = [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 4, 0, 3, 5, 4, 0, 6, 0, 100, 100, 1, 1, 1, 1, 0, 1, 1, 1, 100, 100, 0, 0, 2, 0, 0, 2, 0, 0, 100, 100, 0, 0, 0, 0, 1, 0, 0, 0, 100, 100, 0, 0, -3, 0, -1, 0, 0, 0, 100, 100, 0, 0, -2, 0, 0, -2, 0, 0, 100, 100, -1, -1, -1, -1, 0, 0, -1, -1, 100, 100, -4, 0, -3, -5, -6, 0, 0, -4, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100]
    move_seq = [(35, 55), (85, 65), (27, 46), (97, 76), (22, 43), (92, 73), (26, 53), (96, 63), (53, 86), (95, 86), (25, 27), (86, 95), (26, 25)]
    position = Position(board = board,sgn = -1,move_seq = move_seq, wc = [True,True], bc = [False,False])
    expected = set([(63, 74), (63, 85), (63, 96), (63, 52), (63, 41), (63, 72), (63, 54), (63, 45), (63, 36), (73, 92), (73, 85), (73, 52), (73, 54), (73, 61), (76, 97), (76, 55), (76, 57), (76, 68), (76, 64), (81, 71), (81, 61), (82, 72), (82, 62), (84, 74), (84, 64), (87, 77), (87, 67), (88, 78), (88, 68), (91, 92), (94, 85), (95, 85), (95, 86), (95, 96), (98, 97), (98, 96)])
    print "from generator"
    generated = set(position.make_move_list())
    print printable_moves(generated)
    print "expected"
    print printable_moves(expected)
    assert set(position.make_move_list()) == expected

    board = setup_position(["Ke1,Ra1,Rh1,Nb3,Ng3,Pc2,Pd2,Pe5","Ke8,Bb4,Bf3,Qh4,Pd5"])
    move_seq = [(84,64)]
    position = Position(board = board,sgn = 1,move_seq = move_seq, wc = [True,False],bc = [False,False])
    position.print_board2()
    expected = set([(21, 31),(21, 41),(21, 51),(21, 61),(21, 71),(21, 81),(21, 91),(21, 22),(21, 23),(21, 24),(25, 26),(25, 36),(25, 27),(28, 38),(28, 48),(28, 58),(28, 27),(28, 26),(33, 43),(33, 53),(42, 63),(42, 61),(42, 54),(42, 23),(65, 75),(65, 74)])
    print "from generator"
    generated = set(position.make_move_list())
    print printable_moves(generated)
    print "expected"
    print printable_moves(expected)
    
    assert set(position.make_move_list()) == expected

    #checkmate and stalemate tests
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-5,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,sgn = 1,move_seq = [])
    assert len(position.make_move_list()) == 0
    assert position.king_hanging(None) == True

    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-4,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,sgn = 1,move_seq = [])
    assert len(position.make_move_list()) == 1
    assert position.king_hanging(None) == True
    
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-3,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,sgn = 1,move_seq = [])
    assert len(position.make_move_list()) == 0
    assert position.king_hanging(None) == False
    
    board = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,6,-2,-6,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,0,0,0,0,0,0,0,0,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100]
    position = Position(board = board,sgn = 1,move_seq = [])
    assert len(position.make_move_list()) == 1
    assert position.king_hanging(None) == False
    
    print "testing board set up and printing"
    #board setup and printing test
    new_board = setup_position(['Pa2,Pb2,Ra1,Ke1','Pa7,Ke8'])
    pos = Position(board = new_board)
    pos.print_board2()
    
    print "testing hashing"
    global ht
    ht = dict()    
    zobrist_init()
    
    h = []
    
    pos = Position(initial_board[:])
    assert pos.wc == (False,False)
    assert pos.bc == (True,True)
    assert pos.ep is None
    h1 = zobrist_hash(pos)
    h.append(h1)
    ht["ordered"].append(h1)
    
    move = (27,46) #Ng1-f3
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.wc == (True,True)
    assert pos.bc == (False,False)
    assert pos.ep is None
    
    move = (97,76) #Ng8-f6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (46,27) #Nf3-g1
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (76,97) #Nf6-g8
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert h[0] == h[4]
    
    move = (31,41) #a2-a3
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (84,64) #d7-d5
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (22,43) #b1-c3
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (64,54) #d5-d4
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (35,55) #e2-e4, now ep possible
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.ep == 5
    
    move = (94,84) #Qd8-d7
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (26,53) #Bf1-c4, now ep no longer possible
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert h[8] != h[10]
    
    move = (84,94) #Qd7-d8
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (53,26) #Bc4-f1
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.sgn == -1
    
    assert len(set(h)) == 13
    
    move = (54,43) #d4-c3
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (34,43) #d2-c3
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (94,24) #Qd8-d1
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (25,24) #Ke1-d1
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (93,75) #Bc8-e6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (24,25) #Kd1-e1
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (92,71) #Nb8-a6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.wc == (False,False)
    
    move = (23,67) #Bc1-g5
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.bc == (False,True)
    
    move = (88,68) #h7-h5
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (26,62) #Bf1-b5
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.bc == (False,False)
    
    assert len(set(h)) == 23
    
    move = (83,73) #c7-c6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (62,71) #Bb5-a6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.bc == (False,True)
    
    move = (97,76) #Ng8-f6
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    
    move = (71,82) #Ba6-b7
    h.append(update_hash(pos,h[-1],move)) 
    pos.make_move(move)
    assert pos.bc == (False,False)
    assert len(set(h)) == 27
    
    print "testing perft function"
    position = Position()
    assert perft(position,0) == 1
    position = Position()
    assert perft(position,1) == 20
    position = Position()
    assert perft(position,2) == 400
    position = Position()
    assert perft(position,3) == 8902
    #assert perft(position,4) == 197281
    #assert perft(position,5) == 4865609
    
    def test(num_games,white,black,depth1 = None, depth2 = None,verbose = False,testing = False):
        print "white =",white," black =",black
        if depth1:
            print "white depth =",depth1
        if depth2:
            print "black depth =",depth2
        print "num_games =",num_games
        time0 = time.time()
        white_wins = 0
        black_wins = 0
        draws = 0
        undecided_games = 0
        for count in range(num_games):
            outcome = play_game(500,white,black,verbose = verbose, depth1 = depth1, \
                                depth2 = depth2, testing = testing)
            #print "len(ht) =",len(ht)
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
        print "white average score", white_percentage
    
    #test(1,"random","random",verbose = False)    
    test(1,"random","heuristic",depth1 = None,depth2 = 4,verbose = False) 
    #test(10,"heuristic","random",depth1 = 2,depth2 = None,verbose = False) 
    #manually check that if depth > 1, ts_calls << total number of nodes
    #manually check that ts_calls and quiesce_calls are about the same order of magnitude
    #assert beta_cutoffs != 0
    print "mml_calls =",mml_calls
    print "mml_hash_returns =",mml_hash_returns
    
    print "testing see"
    position = Position(board = initial_board[:])
    assert see(position, 55) == 0
    
    board = setup_position(["Kg1,Qd3,Ra1,Re1,Bd2,Nf3,Pa5,Pc2,Pd5,Pe4,Pf4,Pg3,Ph3",\
                            "Kg8,Qe7,Ra8,Re8,Bb5,Nd7,Nh5,Bg7,Pa6,Pb7,Pc5,Pc4,Pd6,Pf5,Pg6,Ph7"])
    position = Position(board,sgn = -1)
    assert see(position,21) == 2
    assert see(position,44) == 9
    assert see(position,56) == 0
    assert see(position,47) == 1
    assert see(position,55) == 1
    
    
ts_calls = 0
beta_cutoffs = 0
quiesce_calls = 0
mml_calls = 0
mml_hash_returns = 0

cProfile.run("test_suite()")
