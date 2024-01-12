# main.py

import sys
import math
import pygame as pg

from msdraw import draw_border, swap_color, render_cell
from msgui import NumberDisplay, SmileButton
from board import Board
from conf import *


class App:
    """ The main class application, contains methods to manage player
    interactions with the board, and methods to display the current state of
    the board """

    def __init__(self, board_size, mines):
        # Initialize pygame
        pg.init()

        # Increases the maximum recursion limit for cases where the map is
        # too large and the digg recursion exceeds its normal depth limit
        sys.setrecursionlimit(2000)

        self.screen_size = (
            CELL_SIZE * board_size[0] + 25,
            CELL_SIZE * board_size[1] + 64
        )

        self.offset = 13, 56

        self.window = pg.display.set_mode(self.screen_size)
        pg.display.set_caption("Mine Sweeper")

        self.board = Board(board_size, mines)
        self.flags_display = NumberDisplay(self.board.mines_remaining())
        self.clock_display = NumberDisplay(0)

        self.smile_button = SmileButton(
            self, (self.screen_size[0] // 2 - 13, 16),
            self.restart
        )

        self.clock = pg.time.Clock()
        self.start_time = None

        self.background = self.render_background()
        self.cell_symbols = self.render_symbols()

        self.left_click = False
        self.right_click = False
        self.chord_mode = False

        # To mark if the player is able to continue interacting with the board
        self.alive = True
        self.won = False

    def render_background(self):
        """ Generates a pygame surface representing the background """

        w, h = self.screen_size
        surf = pg.Surface((w, h))
        bw, bh = BOARD_SIZE[0] * CELL_SIZE, BOARD_SIZE[1] * CELL_SIZE

        # Main screen border
        draw_border(
            surf, (0, 0), (w + 3, h + 3), 3,
            C_LIGHT_GRAY, C_WHITE, C_GRAY, C_LIGHT_GRAY
        )

        # Top bar border
        draw_border(
            surf, (10, 10), (bw + 6, 37), 2,
            C_LIGHT_GRAY, C_GRAY, C_WHITE, C_LIGHT_GRAY
        )

        # Mines remaining display border
        draw_border(
            surf, (17, 16), (41, 25), 1,
            C_LIGHT_GRAY, C_GRAY, C_WHITE, C_BLACK
        )

        # Time passed display border
        draw_border(
            surf, (bw + 6 - 40, 16), (41, 25), 1,
            C_LIGHT_GRAY, C_GRAY, C_WHITE, C_BLACK
        )

        # Board border
        draw_border(
            surf, (10, 53), (bw + 6, bh + 6), 3,
            C_LIGHT_GRAY, C_GRAY, C_WHITE, C_LIGHT_GRAY
        )

        return surf

    def render_unexplored_cell(self):
        """ Generates a pygame surface representing an unexplored cell """

        size = CELL_SIZE
        surf = pg.Surface((size, size))
        surf.fill(C_LIGHT_GRAY)

        draw_border(
            surf, (0, 0), (size, size), 2,
            C_LIGHT_GRAY, C_WHITE, C_GRAY, C_LIGHT_GRAY
        )

        return surf

    def render_explored_cell(self):
        """ Generates a pygame surface representing an explored cell """

        surf = pg.Surface((CELL_SIZE, CELL_SIZE))
        surf.fill(C_GRAY)

        pg.draw.rect(surf, C_LIGHT_GRAY, (1, 1, CELL_SIZE - 1, CELL_SIZE - 1))

        return surf

    def render_symbols(self):
        """ Loads all the symbols and cache them in custom generated
        surfaces to be used in self.render() """

        symbols = {}

        # Render the base cells
        explored_cell = self.render_explored_cell()
        unexplored_cell = self.render_unexplored_cell()

        # Render all numbers
        for i in range(0, 10):
            symbols[i] = render_cell(
                explored_cell, i, (C_WHITE, NUMBER_COLORS[i])
            )

        # Store the surfaces
        symbols[UNTOUCHED_MINE_CELL] = render_cell(
            explored_cell, 10
        )

        symbols[INCORRECT_MINE_CELL] = render_cell(
            symbols[UNTOUCHED_MINE_CELL], 12, (C_WHITE, C_RED)
        )

        symbols[DETONED_MINE_CELL] = swap_color(
            render_cell(explored_cell, 10), C_LIGHT_GRAY, C_RED
        )

        symbols[FLAG_CELL] = render_cell(
            unexplored_cell, 11, (C_WHITE, C_RED)
        )

        symbols[UNEXPLORED_CELL] = unexplored_cell
        symbols[EXPLORED_CELL] = explored_cell

        return symbols

    def restart(self):
        """ Method to restart the game. Called when the player press 'r'
        or clicks the smile button """
        self.board.__init__(BOARD_SIZE, MINES)
        self.start_time = None

        self.clock_display.set_value(0)

        self.alive = True
        self.won = False

    def on_success_dig(self):
        self.won = self.board.win()

        digg_map = self.board.digg_map

        if not self.start_time and \
                len(digg_map[digg_map == -1]) < BOARD_SIZE[0] * BOARD_SIZE[1]:
            self.start_time = self.get_time()

    def check_events(self):
        """ Method to manage player events:

            If the player press 'ESC', exit the game.
            If the player press 'r', restart the game.

            If the player 'press' left click, digg in a cell.
            If the player press right click, place/remove a flag on a cell.

         """

        self.left_click, _, self.right_click = pg.mouse.get_pressed()

        for event in pg.event.get():
            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()

            if event.type == pg.KEYDOWN:
                # Exit the game and shutdown the program
                if event.key == pg.K_ESCAPE:
                    pg.quit()
                    sys.exit()

                # Reset the game when the player pressed 'r' key
                if event.key == pg.K_r:
                    self.restart()

            # If the player is not alive, skip.
            if not self.alive or self.won:
                continue

            # Event for when the player clicked to place a flag
            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == RIGHT and not self.left_click:
                    self.board.place_flag(self.cell_pos(event.pos))

                    # Update flag display value
                    self.flags_display.set_value(self.board.mines_remaining())

            # Event for when the player clicked to digg a place
            if event.type == pg.MOUSEBUTTONUP:
                # If the chord technique is not active, digg a single cell
                if event.button == LEFT and not self.chord_mode:
                    # Digg the clicked place
                    if not self.board.digg(self.cell_pos(event.pos)):
                        self.end_game()
                        continue

                    self.on_success_dig()

                # If the chord technique is active, digg all the
                # surrounding cells
                if (event.button == LEFT and self.right_click)\
                        or (event.button == RIGHT and self.left_click):
                    # If the chording fails, means that the player wrong placed
                    # a flag and the chording technique digged a mine.
                    if not self.board.chord(self.cell_pos(event.pos)):
                        self.end_game()
                        continue

                    self.on_success_dig()

            if self.won:
                # Places a flag in all unexplored cells
                digg_map = self.board.digg_map
                digg_map[digg_map == UNEXPLORED_CELL] = FLAG_CELL

    def cell_pos(self, pos):
        """ Calculates and returns the cell position from a screen position """
        off_x, off_y = self.offset
        return (pos[0] - off_x) // CELL_SIZE, (pos[1] - off_y) // CELL_SIZE

    def end_game(self):
        """ Finish the game, called when the player stepped on a mine """
        self.board.reveal_mines()
        self.alive = False

    def render_field(self):
        """ Displays the entire field map and also displays """

        board = self.board
        w, h = board.size
        off_x, off_y = self.offset

        # Render the digg_map status of the board
        for i in range(w):
            for j in range(h):
                surf = self.cell_symbols[board.digg_map[i, j]]
                self.window.blit(
                    surf, (i * CELL_SIZE + off_x, j * CELL_SIZE + off_y)
                )

    def render_click_effects(self):
        """ Displays effects for when the player is holding click to digg
        a cell and displays the effect of the player holding both clicks to
        make a chord technique """

        board = self.board
        w, h = board.size
        off_x, off_y = self.offset

        # If the player isn't alive, stop proccess
        if not self.alive or self.won:
            return

        # If the mouse position isn't inside the board, skip the next actions
        x, y = self.cell_pos(pg.mouse.get_pos())
        if not board.inside_board((x, y)):
            return

        # Turn on chord mode if both clicks are pressing
        if self.left_click and self.right_click:
            self.chord_mode = True

            # Replace all surrounding cells from (x, y) with explored_cell
            for i in range(-1, 2):
                for j in range(-1, 2):
                    if not board.inside_board((x + i, y + j)):
                        continue
                    if board.digg_map[x + i, y + j] != -1:
                        continue

                    self.window.blit(
                        self.cell_symbols[EXPLORED_CELL],
                        ((x + i)*CELL_SIZE + off_x, (y + j)*CELL_SIZE + off_y)
                    )

        # Turn off chord mode if clicks are no longer holding
        if not self.left_click and not self.right_click:
            self.chord_mode = False

        # Single cell dig mode
        if self.left_click and not self.chord_mode:
            if board.digg_map[x, y] == -1:
                self.window.blit(
                    self.cell_symbols[EXPLORED_CELL],
                    (x * CELL_SIZE + off_x, y * CELL_SIZE + off_y)
                )

    def render_displays(self):
        bw, bh = BOARD_SIZE[0] * CELL_SIZE, BOARD_SIZE[1] * CELL_SIZE

        # Update and render remaining mines display
        self.flags_display.set_value(self.board.mines_remaining())
        self.window.blit(self.flags_display.surf, (18, 17))

        # Update and render clock display
        if self.start_time and not self.won and self.alive:
            time = int(self.get_time() - self.start_time)
            self.clock_display.set_value(time)

        self.window.blit(self.clock_display.surf, (bw - 33, 17))

    def render(self):
        """ Contains render methods to display the game """
        self.window.blit(self.background, (0, 0))

        self.render_field()
        self.render_click_effects()
        self.render_displays()

        self.smile_button.draw(self.window)

        pg.display.flip()

    def get_time(self):
        return pg.time.get_ticks() * 0.001

    def start(self):
        """ Starts the main loop of the game """
        while True:
            self.check_events()
            self.render()
            self.clock.tick(GAME_FPS)


def main():
    app = App(BOARD_SIZE, MINES)
    app.start()


if __name__ == '__main__':
    main()
