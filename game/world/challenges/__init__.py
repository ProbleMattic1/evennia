"""
Cadence-challenge subsystem.

Separate from narrative missions (typeclasses/missions.py). Handles time-windowed
goals (daily → yearly) backed by economy, property, hauler, and navigation events.

Public entry points:
  from world.challenges.challenge_loader import load_challenge_templates, get_challenge_template
  from world.challenges.challenge_handler import ChallengeHandler
  from world.challenges.challenge_signals import emit
  from world.challenges.challenge_evaluator import on_event, evaluate_window
"""
