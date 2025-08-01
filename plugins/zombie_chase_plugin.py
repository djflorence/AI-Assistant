"""Zombie Chase Game Plugin."""

import random
import pygame


def plugin_info():
    return {
        'name': 'Zombie Chase Game',
        'description': 'Play a simple zombie chase survival game'
    }


def get_commands():
    return {
        'play_game': {
            'function': play_game,
            'description': 'Launch the zombie chase game'
        }
    }


def play_game():
    """Launch a small zombie chase game window."""
    pygame.init()
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption('Zombie Chase')

    player_size = 30
    player = pygame.Rect(width // 2, height // 2, player_size, player_size)
    player_speed = 5

    zombie_size = 30
    zombies = []
    spawn_timer = 0
    spawn_delay = 2000  # milliseconds
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    start_ticks = pygame.time.get_ticks()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.x -= player_speed
        if keys[pygame.K_RIGHT]:
            player.x += player_speed
        if keys[pygame.K_UP]:
            player.y -= player_speed
        if keys[pygame.K_DOWN]:
            player.y += player_speed

        player.x = max(0, min(width - player_size, player.x))
        player.y = max(0, min(height - player_size, player.y))

        current_time = pygame.time.get_ticks()
        if current_time - spawn_timer > spawn_delay:
            spawn_timer = current_time
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top':
                x = random.randint(0, width - zombie_size)
                y = -zombie_size
            elif side == 'bottom':
                x = random.randint(0, width - zombie_size)
                y = height + zombie_size
            elif side == 'left':
                x = -zombie_size
                y = random.randint(0, height - zombie_size)
            else:
                x = width + zombie_size
                y = random.randint(0, height - zombie_size)
            zombies.append(pygame.Rect(x, y, zombie_size, zombie_size))

        for z in zombies:
            dx = player.x - z.x
            dy = player.y - z.y
            dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)
            speed = 2
            z.x += int(speed * dx / dist)
            z.y += int(speed * dy / dist)

        for z in zombies:
            if z.colliderect(player):
                running = False

        screen.fill((30, 30, 30))
        pygame.draw.rect(screen, (0, 255, 0), player)
        for z in zombies:
            pygame.draw.rect(screen, (255, 0, 0), z)

        timer_text = font.render(
            f"Time: {(current_time - start_ticks) / 1000:.2f}", True, (255, 255, 255)
        )
        screen.blit(timer_text, (10, 10))

        if not running:
            game_over = font.render(
                f"Game Over! Survived {(current_time - start_ticks) / 1000:.2f}s",
                True,
                (255, 0, 0),
            )
            screen.blit(
                game_over,
                (
                    width // 2 - game_over.get_width() // 2,
                    height // 2 - game_over.get_height() // 2,
                ),
            )
            pygame.display.flip()
            pygame.time.wait(3000)
            break

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 'Game ended'
