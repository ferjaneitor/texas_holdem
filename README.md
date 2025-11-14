# Texas Hold'em Poker (Pygame)

Proyecto de juego de Texas Hold'em escrito en Python usando Pygame, con bots controlados por IA y una interfaz gráfica completa.

---

## 🃏 Descripción

Este proyecto implementa una mesa de Texas Hold'em para 1 jugador humano contra varios bots. Incluye:

- Motor de juego completo (rondas, apuestas, showdown).
- IA con diferentes niveles de dificultad.
- Interfaz gráfica con Pygame (mesa, cartas, HUD, lobby).
- Sistema de logging a consola y archivo (`hand_history.log`).

---

## 📂 Estructura del Proyecto

- [`main.py`](main.py)  
  Punto de entrada. Inicializa el logging y arranca el loop principal con [`game_logic.game.Game`](game_logic/game.py).

- [`config.py`](config.py)  
  Constantes de configuración:
  - Dimensiones de la ventana (`WIDTH`, `HEIGHT`, `FPS`).
  - Colores y tamaños (`TABLE_COLOR`, `CARD_W`, `CARD_H`, `FOOTER_H`, `PLAYER_Y`, `BOT_MAX_Y`).
  - Economía (`STARTING_STACK`, `SMALL_BLIND`, `BIG_BLIND`, `MAX_BOTS`).
  - Flags de recompra (`ARCADE_REBUY`, `AUTO_REBUY_BOTS`).
  - Tiempos y dificultad (`BOT_THINK_MS`, `BOT_POST_ACT_PAUSE`, `BANNER_MS`, `EASY`, `MED`, `HARD`).

- [`utils.py`](utils.py)  
  Utilidades generales:
  - [`utils.clamp`](utils.py): limita valores a un rango.
  - [`utils.setup_logging`](utils.py): configura logging a stdout y archivo.

- [`cards.py`](cards.py)  
  Modelo de cartas y baraja:
  - Constantes de palos y rangos.
  - Clase [`cards.Card`](cards.py).
  - Clase [`cards.Deck`](cards.py).

- [`player.py`](player.py)  
  Modelo de jugador:
  - Clase [`player.Player`](player.py) con estado de stack, cartas, apuestas, flags `folded` / `all_in`.

- [`eval_hand.py`](eval_hand.py)  
  Evaluación de manos:
  - [`eval_hand.is_straight`](eval_hand.py): detección de escaleras.
  - [`eval_hand.evaluate7`](eval_hand.py): evalúa la mejor mano de 5 cartas entre 7.
  - [`eval_hand.quick_strength`](eval_hand.py): heurística de fuerza de mano para la IA.

- [`ai.py`](ai.py)  
  Lógica de IA:
  - [`ai.bot_decision`](ai.py): decide acción del bot (`fold`, `call`, `raise_to`, `allin`) según:
    - Fuerza de mano (`quick_strength`).
    - Cantidad a pagar (`to_call`).
    - Tamaño del bote.
    - Dificultad (`EASY`, `MED`, `HARD`).

- [`ui.py`](ui.py)  
  Componentes de interfaz:
  - Clase [`ui.Button`](ui.py) para los botones clickeables.

- [`game_logic/`](game_logic/__init__.py)  
  Contiene el controlador principal del juego y mixins:

  - [`game_logic/game.py`](game_logic/game.py)  
    Clase principal [`game_logic.game.Game`](game_logic/game.py):
    - Inicializa Pygame, fuentes, pantalla.
    - Gestiona el loop principal (`Game.run`).
    - Mantiene todo el estado del juego (jugadores, pot, board, etc.).
    - Hereda de varios mixins para separar responsabilidades.

  - [`game_logic/logger.py`](game_logic/logger.py)  
    [`game_logic.logger.LoggerMixin`](game_logic/logger.py):
    - [`round_label`](game_logic/logger.py): etiqueta de ronda (Flop/Turn/River/Showdown).
    - [`banner`](game_logic/logger.py): texto flotante en pantalla.
    - [`push_log`](game_logic/logger.py): agrega mensajes al log (UI + logging Python).
    - [`dump_state`](game_logic/logger.py): vuelca el estado interno para debug.

  - [`game_logic/lobby.py`](game_logic/lobby.py)  
    [`game_logic.lobby.LobbyMixin`](game_logic/lobby.py):
    - Lobby de inicio para:
      - Elegir número de bots (`num_bots`).
      - Elegir dificultad (`bot_difficulty`).
    - Botones de lobby y “Empezar” (`make_lobby_buttons`).
    - Volver al lobby (`return_to_lobby`).
    - Botón de continuar entre rondas (`make_continue_button`).

  - [`game_logic/keypad.py`](game_logic/keypad.py)  
    [`game_logic.keypad.KeypadMixin`](game_logic/keypad.py):
    - Teclado modal para seleccionar tamaño de apuesta (“Aumentar”).
    - Lógica de límites de subida:
      - Funciones `can_allin_now`, `pre_river_cap_target`.
      - Botones rápidos: Igualar, −BB, +BB, Pote, All-in (o All-in cap).
    - Cálculo de máximo permitido antes del river (cap de bote).

  - [`game_logic/renderer.py`](game_logic/renderer.py)  
    [`game_logic.renderer.RendererMixin`](game_logic/renderer.py):
    - Dibujo de fondo y mesa (`draw_gradient_bg`, `draw_table`).
    - Render de cartas (`draw_card`, `draw_hand_cards`, `draw_board`).
    - Render de jugadores y HUD (`draw_players`, `draw_hud`).
    - Creación de botones de acción (`make_action_buttons`).
    - Bucle de render principal (`draw`).
    - Actualización de timers y turno de bots (`update`).

  - [`game_logic/state.py`](game_logic/state.py)  
    [`game_logic.state.StateMixin`](game_logic/state.py):
    - Setup inicial de jugadores (`setup_players`).
    - Inicio de mano (`start_hand`):
      - Recompras automáticas (`AUTO_REBUY_BOTS`).
      - Reparto de hole cards y board.
      - Colocación de ciegas (`post_blinds`).
      - Inicialización de estado de ronda y variables visuales.
    - Continuación tras pausas y fin de mano (`continue_after_pause`).

  - [`game_logic/betting.py`](game_logic/betting.py)  
    [`game_logic.betting.BettingMixin`](game_logic/betting.py):
    - Motor de apuestas:
      - Gestión de `current_bet`, `last_raiser`, `last_raise_size`.
      - Conjunto `pending_to_act` para saber quién debe actuar.
      - Lógica de cambio de calle (`proceed_round`).
    - Acciones de jugador humano:
      - `player_action_fold`, `player_action_call`,
        `player_action_raise_to`, `player_action_allin`.
    - Turno de bots:
      - `bot_take_turn_if_needed`: integra la decisión de [`ai.bot_decision`](ai.py).

  - [`game_logic/showdown.py`](game_logic/showdown.py)  
    [`game_logic.showdown.ShowdownMixin`](game_logic/showdown.py):
    - Lógica de showdown:
      - Si solo queda uno sin foldear, gana sin mostrar.
      - Si hay varios contendientes:
        - Usa [`eval_hand.evaluate7`](eval_hand.py).
        - Reparte el bote (incluye empates y restos).

---

## 🧪 Requisitos

- Python 3.8 o superior.
- Pygame instalado.

Instalación de Pygame:

```bash
pip install pygame
```

---

## ▶️ Cómo ejecutar

En la carpeta del proyecto:

```bash
python main.py
```

Esto hará:

1. Configurar el logging mediante [`utils.setup_logging`](utils.py) (archivo `hand_history.log`).
2. Crear una instancia de [`game_logic.game.Game`](game_logic/game.py).
3. Entrar al loop del juego con `Game().run()`.

---

## 🎮 Cómo jugar

### Lobby

Al iniciar, verás el lobby:

- Elige número de bots (`num_bots`) con los botones “−” y “+”.
- Elige dificultad:
  - [`config.EASY`](config.py): “Fácil”
  - [`config.MED`](config.py): “Media”
  - [`config.HARD`](config.py): “Difícil”
- Pulsa **“Empezar”** para sentarte en la mesa.

### En la mesa

En la parte inferior aparecerán los botones de acción, creados por  
[`game_logic.renderer.RendererMixin.make_action_buttons`](game_logic/renderer.py):

- **Retirarse**: abandonar la mano (`player_action_fold`).
- **Pasar / Igualar**: según si hay apuesta por igualar (`player_action_call`).
- **Aumentar**: abre el teclado de subida (`open_keypad` → [`game_logic.keypad.KeypadMixin`](game_logic/keypad.py)).
- **All-in**: solo permitido en la última ronda (river), controlado por `can_allin_now`.
- **Menu**: volver al lobby (`return_to_lobby`).

En el HUD se muestra:

- Pote actual.
- Fase: Flop / Turn / River / Showdown.
- Dificultad de bots.
- Tu stack y “A igualar”.
- Historial de acciones (últimos mensajes).
- Mensajes de banner (acciones importantes, ganador de la mano, etc.).

---

## ⚙️ Configuración rápida

Modifica [`config.py`](config.py) para ajustar:

- Ciegas y stack inicial:

```python
STARTING_STACK = 500
SMALL_BLIND = 10
BIG_BLIND = 20
```

- Número máximo de bots:

```python
MAX_BOTS = 7
```

- Recompras:

```python
ARCADE_REBUY = True        # El jugador se recarga si se queda sin fichas
AUTO_REBUY_BOTS = True     # Bots se recargan al inicio de mano si tienen menos que la BB
```

- Velocidad de bots:

```python
BOT_THINK_MS = 900         # tiempo de "pensando..."
BOT_POST_ACT_PAUSE = 800   # pausa tras actuar
```

---

## 🧠 IA de Bots

La función [`ai.bot_decision`](ai.py) usa:

- Fuerza aproximada de mano con [`eval_hand.quick_strength`](eval_hand.py).
- Parámetros por dificultad (`EASY`, `MED`, `HARD`):
  - Umbrales de fold/raise.
  - Probabilidad de farol (`bluff_chance`).
  - Factor de agresividad (`raise_factor`).
- Presión del bote para adaptar el juego (más bote → menos farol / más cuidado).

Devuelve una acción:

- `'fold'`
- `'call'`
- `'raise_to'` (subir a una cantidad total de apuesta)
- `'allin'`

Que luego se ejecuta en [`game_logic.betting.BettingMixin.bot_take_turn_if_needed`](game_logic/betting.py).

---

## 📝 Logging

- Toda la actividad del juego se envía a:
  - Consola estándar.
  - Archivo `hand_history.log`.

Configurado en [`utils.setup_logging`](utils.py) y usado desde [`game_logic.logger.LoggerMixin`](game_logic/logger.py).

---

## 📌 Notas

- No hay soporte de botes secundarios (side pots); los all-in múltiples se manejan con un bote simple.
- El all-in está restringido a la última ronda (river) para simplificar la lógica de apuestas. Antes del river, las subidas están “capadas” con `pre_river_cap_target`.

---

¡Disfruta mejorando y personalizando tu juego de Texas Hold'em!