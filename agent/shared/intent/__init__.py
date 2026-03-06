# shared/intent/__init__.py
# Exports dos módulos de intenção

from shared.intent.coherence_tracker import CoherenceTracker
from shared.intent.ambiguity_resolver import AmbiguityResolver
from shared.intent.transcendence_tracker import TranscendenceTracker
from shared.intent.decision_learner import DecisionLearner
from shared.intent.rule_proposer import RuleProposer, RuleProposal
from shared.intent.growth_horizon import GrowthHorizon
from shared.intent.intentional_friction import IntentionalFriction
from shared.intent.conversation_analyzer import ConversationAnalyzer
from shared.intent.profile_builder import ProfileBuilder
from shared.intent.behavioral_pattern_detector import BehavioralPatternDetector
from shared.intent.intent_engine import IntentEngine
from shared.intent.scope_learner import ScopeLearner, HorizonRealismTracker, PatternResistanceDetector

__all__ = [
    "CoherenceTracker",
    "AmbiguityResolver", 
    "TranscendenceTracker",
    "DecisionLearner",
    "RuleProposer",
    "RuleProposal",
    "GrowthHorizon",
    "IntentionalFriction",
    "ConversationAnalyzer",
    "ProfileBuilder",
    "BehavioralPatternDetector",
    "IntentEngine",
    "ScopeLearner",
    "HorizonRealismTracker",
    "PatternResistanceDetector",
]
