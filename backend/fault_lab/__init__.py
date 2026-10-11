"""Fault Lab — an independently deployable HTTP fault & diagnostic simulator.

The simulator controls only two things: the HTTP behaviour of the /health
target it exposes, and the diagnostic snapshot it serves to the Agent. It keeps
AlertFlow's monitoring, Incident creation and Agent forensics out of scope.
"""

__version__ = "1.0.0"
