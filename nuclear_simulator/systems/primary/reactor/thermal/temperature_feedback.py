"""
Temperature Feedback Model

This module implements temperature feedback mechanisms for nuclear reactor simulation,
including Doppler feedback and moderator temperature effects on reactivity.
"""

from typing import Dict


class TemperatureFeedbackModel:
    """
    Temperature feedback model for nuclear reactor reactivity effects
    """

    def __init__(self):
        """Initialize temperature feedback model with coefficients"""
        # Temperature feedback coefficients
        self.doppler_coefficient = -2.5e-5  # Δρ/ΔT_fuel (1/°C)
        self.moderator_temp_coeff = -3.0e-5  # Δρ/ΔT_mod (1/°C)
        
        # Reference conditions
        self.ref_fuel_temperature = 575.0  # °C
        self.ref_coolant_temperature = 280.0  # °C

    def calculate_doppler_feedback(self, fuel_temperature: float) -> float:
        """
        Calculate Doppler reactivity feedback from fuel temperature
        
        Args:
            fuel_temperature: Current fuel temperature in °C
            
        Returns:
            Doppler reactivity feedback in pcm
        """
        delta_temp = fuel_temperature - self.ref_fuel_temperature
        reactivity = self.doppler_coefficient * delta_temp * 1e5  # Convert to pcm
        
        return reactivity

    def calculate_moderator_temperature_feedback(self, coolant_temperature: float) -> float:
        """
        Calculate moderator temperature reactivity feedback
        
        Args:
            coolant_temperature: Current coolant temperature in °C
            
        Returns:
            Moderator temperature reactivity feedback in pcm
        """
        delta_temp = coolant_temperature - self.ref_coolant_temperature
        reactivity = self.moderator_temp_coeff * delta_temp * 1e5  # Convert to pcm
        
        return reactivity

    def calculate_total_temperature_feedback(self, reactor_state) -> Dict[str, float]:
        """
        Calculate total temperature feedback effects
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Dictionary with temperature feedback components
        """
        doppler_feedback = self.calculate_doppler_feedback(reactor_state.fuel_temperature)
        moderator_feedback = self.calculate_moderator_temperature_feedback(
            reactor_state.coolant_temperature
        )
        
        total_feedback = doppler_feedback + moderator_feedback
        
        return {
            "doppler_feedback_pcm": doppler_feedback,
            "moderator_temp_feedback_pcm": moderator_feedback,
            "total_temp_feedback_pcm": total_feedback,
            "fuel_temp_delta": reactor_state.fuel_temperature - self.ref_fuel_temperature,
            "coolant_temp_delta": reactor_state.coolant_temperature - self.ref_coolant_temperature,
        }

    def get_temperature_coefficients(self) -> Dict[str, float]:
        """
        Get temperature feedback coefficients
        
        Returns:
            Dictionary with temperature coefficients
        """
        return {
            "doppler_coefficient": self.doppler_coefficient,
            "moderator_temp_coefficient": self.moderator_temp_coeff,
            "ref_fuel_temperature": self.ref_fuel_temperature,
            "ref_coolant_temperature": self.ref_coolant_temperature,
        }

    def set_temperature_coefficients(
        self, 
        doppler_coeff: float = None, 
        moderator_coeff: float = None
    ) -> None:
        """
        Set temperature feedback coefficients
        
        Args:
            doppler_coeff: Doppler coefficient in 1/°C (optional)
            moderator_coeff: Moderator temperature coefficient in 1/°C (optional)
        """
        if doppler_coeff is not None:
            self.doppler_coefficient = doppler_coeff
        
        if moderator_coeff is not None:
            self.moderator_temp_coeff = moderator_coeff

    def validate_temperature_feedback(self, reactor_state) -> bool:
        """
        Validate temperature feedback calculations
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            True if feedback calculations are valid, False otherwise
        """
        # Check for reasonable temperature ranges
        if reactor_state.fuel_temperature < 200 or reactor_state.fuel_temperature > 2000:
            return False
        
        if reactor_state.coolant_temperature < 200 or reactor_state.coolant_temperature > 400:
            return False
        
        # Calculate feedback and check for reasonable values
        feedback = self.calculate_total_temperature_feedback(reactor_state)
        total_feedback = feedback["total_temp_feedback_pcm"]
        
        # Temperature feedback should typically be negative and within reasonable bounds
        if abs(total_feedback) > 10000:  # More than 10000 pcm seems unreasonable
            return False
        
        return True

    def get_feedback_summary(self, reactor_state) -> str:
        """
        Generate a formatted summary of temperature feedback effects
        
        Args:
            reactor_state: Current reactor state
            
        Returns:
            Formatted string with temperature feedback summary
        """
        feedback = self.calculate_total_temperature_feedback(reactor_state)
        
        summary = "Temperature Feedback Summary:\n"
        summary += "=" * 40 + "\n"
        summary += f"Fuel Temperature: {reactor_state.fuel_temperature:.1f}°C "
        summary += f"(Δ{feedback['fuel_temp_delta']:+.1f}°C)\n"
        summary += f"Coolant Temperature: {reactor_state.coolant_temperature:.1f}°C "
        summary += f"(Δ{feedback['coolant_temp_delta']:+.1f}°C)\n"
        summary += "-" * 40 + "\n"
        summary += f"Doppler Feedback: {feedback['doppler_feedback_pcm']:+.1f} pcm\n"
        summary += f"Moderator Temp Feedback: {feedback['moderator_temp_feedback_pcm']:+.1f} pcm\n"
        summary += "-" * 40 + "\n"
        summary += f"Total Temperature Feedback: {feedback['total_temp_feedback_pcm']:+.1f} pcm\n"
        
        return summary
