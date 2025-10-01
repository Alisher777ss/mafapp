# Mafia Game - Multiplayer Web Application

## Overview

This is a web-based multiplayer implementation of the classic Mafia party game built with Flask. Players can create or join game rooms using unique room codes, where they're assigned roles (either Mafia or Civilian) and participate in day/night cycles to eliminate opposing players. The game features real-time updates, role-based gameplay mechanics, and a comprehensive game log tracking all actions.

## Recent Changes (October 2025)

### Latest Update - New Roles, Game End & Real-time Chat
- **Detective Role** (≥5 players): Investigates one player each night to learn their role; results shown privately
- **Doctor Role** (≥7 players): Can save one player each night from Mafia attack; Doctor save occurs before Mafia kill
- **Game End Screen**: Animated overlay displaying winner (Mafia or Civilians) with restart/exit options
- **Real-time Chat System**: 
  - Slide-in drawer UI with toggle button (top-right corner)
  - Polling-based updates (1.5s interval, active only when chat is open)
  - Role-claim filtering: Blocks messages claiming roles in Uzbek/Russian/English (e.g., "men mafia", "я комиссар", "i'm detective")
  - Security: Only alive players can post; XSS prevention with textContent rendering; membership validation
- **UI Rebrand**: Application name changed from "Mafia Oyini" to "Mafia"

### Previous Updates - Among Us Style Enhancements
- **Timer System**: Added 60-second countdown timer for night and voting phases with warning animations
- **Role Reveal Animation**: Among Us-style animated role reveal screen with custom styling for Mafia/Civilian roles
- **Death Screen**: "YOU DIED" overlay with spectate/exit options, shows kill method (don vs vote)
- **Target Selection UI**: Shows selected victim/vote and hides options after selection
- **Comprehensive Animations**: fadeIn, scaleIn, slideDown, pulse, bounce, glitch animations for immersive gameplay
- **Don Kill Messages**: Displays "(player) was killed by Don" without revealing Don's identity
- **Spectator Mode**: Dead players can continue watching the game
- **Security Fix**: Selected mafia target now only visible to mafia players (prevents information leakage)

### Previous Updates
- Implemented host-based authorization system with persistent host_id
- Fixed mafia targeting bug by properly filtering alive players excluding current player
- Added server-side validation for all critical game actions (start game, execute night, execute vote, phase transitions)
- Enhanced game_state endpoint to include player_id for proper client-side filtering
- Added target validation in night actions to prevent invalid eliminations

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Single Page Application Pattern**: The application uses a hybrid approach with server-side template rendering (Jinja2) combined with client-side JavaScript for dynamic updates. Key pages include:
- `index.html` - Landing page for creating/joining games
- `game.html` - Main gameplay interface

**Client-Side State Management**: JavaScript maintains local state (current phase, player role, host status) and periodically polls the server for game state updates via AJAX requests.

**UI Framework**: Custom CSS with gradient backgrounds and card-based layouts. Uses vanilla JavaScript for DOM manipulation and fetch API for server communication.

### Backend Architecture

**Framework**: Flask web framework chosen for its simplicity and rapid development capabilities for real-time multiplayer games.

**Session Management**: Uses Flask's built-in session management with a UUID-generated secret key for player identification and authentication. Each player receives a unique session ID stored in browser cookies.

**Game State Pattern**: Implemented through the `MafiaGame` class which encapsulates all game logic:
- Player management (add, remove, track status)
- Role assignment with dynamic distribution:
  - 1 Mafia per 3 players
  - 1 Detective if ≥5 players
  - 1 Doctor if ≥7 players
- Phase management (waiting → night → day cycles)
- Night action resolution (Doctor save → Mafia kill → Detective investigation)
- Voting and elimination mechanics
- Game logging for action history
- Win condition checking (all Mafia eliminated or Mafia ≥ Civilians)

**In-Memory Storage**: Game state is stored in a global `games` dictionary using room codes as keys. This design choice prioritizes:
- **Pros**: Simple implementation, fast access, no database overhead
- **Cons**: Data lost on server restart, no persistence, limited scalability

**Alternative Considered**: Using Redis or a database for persistence was considered but rejected for initial MVP to reduce complexity.

### Data Models

**Game Object Structure**:
- `room_code`: Unique identifier for game rooms
- `host_id`: Session ID of game creator
- `players`: List of player dictionaries containing id, name, role, and alive status
- `phase`: Current game state (waiting, night, day)
- `votes`: Dictionary tracking player votes during day phase
- `game_log`: Array of game events for display

**Player Object Structure**:
- `id`: Unique session identifier
- `name`: Display name
- `role`: Either 'mafia', 'civilian', 'detective', or 'doctor'
- `alive`: Boolean status

### API Design

**RESTful Endpoints**:
- `POST /create_game`: Creates new game room, returns room code
- `POST /join_game`: Adds player to existing room
- `GET /game/<room_code>`: Renders game interface
- `GET /game_state/<room_code>`: Returns current game state as JSON (includes player_id for client-side filtering)
- `POST /start_game`: Initiates game (host-only, ≥4 players required)
- `POST /night_action`: Handles night actions (Mafia kill, Doctor save, Detective investigate)
- `POST /vote`: Records player votes during day phase
- `POST /execute_night`: Processes night actions in order (Doctor → Mafia → Detective)
- `POST /execute_vote`: Tallies votes and eliminates player with most votes
- `GET /chat/<room_code>`: Fetches chat messages (incremental with since_id parameter)
- `POST /chat/<room_code>`: Posts chat message (validates membership, alive status, filters role claims)

### Authentication & Authorization

**Session-Based Authentication**: Players are identified by Flask session cookies. The host is determined by comparing session ID with the stored `host_id` in the game object.

**Role-Based Actions**: Player roles (mafia/civilian) determine which actions are available during different phases, enforced server-side.

## External Dependencies

**Python Libraries**:
- `Flask`: Core web framework for routing, templating, and session management
- `uuid`: Generates unique identifiers for secret keys and player sessions
- `random`: Used for role assignment shuffling
- `datetime`: Timestamp tracking for game events

**Frontend Technologies**:
- Vanilla JavaScript (ES6+): No frontend framework dependencies
- Fetch API: For asynchronous server communication
- CSS3: Custom styling with gradients and flexbox layouts

**No External Services**: The application currently runs standalone without database, authentication services, or third-party APIs. All game state is managed in-memory on the Flask server.

**Localization**: UI text is in Uzbek language ("uz" locale), indicating target audience.