"""
Test for Gaussian white noise functionality in ConstantHeatSource
"""

import sys
import numpy as np
import matplotlib.pyplot as plt

sys.path.append('.')

from systems.primary.reactor.heat_sources.constant_heat_source import ConstantHeatSource


def test_noise_functionality():
    """Test the noise functionality of the constant heat source"""
    print("Testing Constant Heat Source with Gaussian White Noise")
    print("=" * 60)
    
    # Test 1: Basic noise functionality
    print("\n1. Testing basic noise functionality")
    print("-" * 40)
    
    # Create heat source with noise enabled
    heat_source = ConstantHeatSource(
        rated_power_mw=3000.0,
        noise_enabled=True,
        noise_std_percent=1.0,  # 1% noise
        noise_seed=1234,  # Reproducible results for testing
        noise_filter_time_constant=10.0  # 10-second filter
    )
    
    print(f"Heat source created: {heat_source}")
    print(f"Noise enabled: {heat_source.noise_enabled}")
    print(f"Noise std: {heat_source.noise_std_percent}%")
    print(f"Filter time constant: {heat_source.noise_filter_time_constant}s")
    
    # Test 2: Run simulation and collect data
    print("\n2. Running simulation to collect noise data")
    print("-" * 40)
    
    dt = 1.0  # 1 second time steps
    duration = 300  # 5 minutes
    time_steps = int(duration / dt)
    
    # Data collection arrays
    times = []
    base_powers = []
    final_powers = []
    raw_noise = []
    filtered_noise = []
    
    for i in range(time_steps):
        result = heat_source.update(dt)
        state = heat_source.get_state_dict()
        
        times.append(heat_source.time)
        base_powers.append(state['base_power_mw'])
        final_powers.append(state['thermal_power_mw'])
        raw_noise.append(state['raw_noise_mw'])
        filtered_noise.append(state['filtered_noise_mw'])
    
    # Convert to numpy arrays for analysis
    times = np.array(times)
    base_powers = np.array(base_powers)
    final_powers = np.array(final_powers)
    raw_noise = np.array(raw_noise)
    filtered_noise = np.array(filtered_noise)
    
    print(f"Simulation completed: {time_steps} time steps")
    print(f"Base power (constant): {base_powers[0]:.1f} MW")
    print(f"Final power range: {final_powers.min():.1f} - {final_powers.max():.1f} MW")
    
    # Test 3: Statistical analysis
    print("\n3. Statistical analysis of noise")
    print("-" * 40)
    
    # Raw noise statistics
    raw_mean = np.mean(raw_noise)
    raw_std = np.std(raw_noise)
    expected_std = (heat_source.noise_std_percent / 100.0) * base_powers[0]
    
    print(f"Raw noise statistics:")
    print(f"  Mean: {raw_mean:.2f} MW (should be ~0)")
    print(f"  Std Dev: {raw_std:.2f} MW (expected: {expected_std:.2f} MW)")
    print(f"  Min/Max: {raw_noise.min():.2f} / {raw_noise.max():.2f} MW")
    
    # Filtered noise statistics
    filtered_mean = np.mean(filtered_noise)
    filtered_std = np.std(filtered_noise)
    
    print(f"\nFiltered noise statistics:")
    print(f"  Mean: {filtered_mean:.2f} MW (should be ~0)")
    print(f"  Std Dev: {filtered_std:.2f} MW (should be < raw std)")
    print(f"  Min/Max: {filtered_noise.min():.2f} / {filtered_noise.max():.2f} MW")
    
    # Final power statistics
    final_mean = np.mean(final_powers)
    final_std = np.std(final_powers)
    
    print(f"\nFinal power statistics:")
    print(f"  Mean: {final_mean:.2f} MW (should be ~{base_powers[0]:.1f} MW)")
    print(f"  Std Dev: {final_std:.2f} MW")
    print(f"  Min/Max: {final_powers.min():.2f} / {final_powers.max():.2f} MW")
    
    # Test 4: Verify filtering effect
    print("\n4. Verifying low-pass filter effect")
    print("-" * 40)
    
    # Calculate filter effectiveness (filtered should be smoother than raw)
    raw_diff = np.abs(np.diff(raw_noise))
    filtered_diff = np.abs(np.diff(filtered_noise))
    
    raw_roughness = np.mean(raw_diff)
    filtered_roughness = np.mean(filtered_diff)
    
    print(f"Noise roughness (mean absolute difference between steps):")
    print(f"  Raw noise: {raw_roughness:.3f} MW/step")
    print(f"  Filtered noise: {filtered_roughness:.3f} MW/step")
    print(f"  Smoothing factor: {raw_roughness/filtered_roughness:.1f}x")
    
    # Test 5: Test without noise
    print("\n5. Testing without noise (baseline)")
    print("-" * 40)
    
    heat_source_no_noise = ConstantHeatSource(
        rated_power_mw=3000.0,
        noise_enabled=False
    )
    
    result_no_noise = heat_source_no_noise.update(dt=1.0)
    print(f"No-noise heat source: {heat_source_no_noise}")
    print(f"Power output: {result_no_noise['thermal_power_mw']:.1f} MW")
    print(f"Noise in result: {result_no_noise.get('filtered_noise_mw', 'N/A')}")
    
    # Test 6: Test different noise levels
    print("\n6. Testing different noise levels")
    print("-" * 40)
    
    noise_levels = [0.1, 0.5, 1.0, 2.0]  # Different noise percentages
    
    for noise_pct in noise_levels:
        test_source = ConstantHeatSource(
            rated_power_mw=3000.0,
            noise_enabled=True,
            noise_std_percent=noise_pct,
            noise_seed=42
        )
        
        # Run a few steps to get noise
        for _ in range(10):
            test_source.update(dt=1.0)
        
        state = test_source.get_state_dict()
        print(f"  {noise_pct:3.1f}% noise: Power = {state['thermal_power_mw']:.1f} MW, "
              f"Noise = {state['filtered_noise_mw']:+.1f} MW")
    
    # Test 7: Test reproducibility with seeds
    print("\n7. Testing reproducibility with seeds")
    print("-" * 40)
    
    # Create two identical heat sources with same seed
    source1 = ConstantHeatSource(noise_enabled=True, noise_seed=123)
    source2 = ConstantHeatSource(noise_enabled=True, noise_seed=123)
    
    # Run them for a few steps
    powers1 = []
    powers2 = []
    
    for _ in range(5):
        result1 = source1.update(dt=1.0)
        result2 = source2.update(dt=1.0)
        powers1.append(result1['thermal_power_mw'])
        powers2.append(result2['thermal_power_mw'])
    
    print("Reproducibility test (same seed):")
    for i, (p1, p2) in enumerate(zip(powers1, powers2)):
        print(f"  Step {i+1}: Source1={p1:.3f} MW, Source2={p2:.3f} MW, Diff={abs(p1-p2):.6f}")
    
    # Validation checks
    print("\n" + "="*60)
    print("VALIDATION RESULTS")
    print("="*60)
    
    checks_passed = 0
    total_checks = 0
    
    # Check 1: Raw noise mean should be close to zero
    total_checks += 1
    if abs(raw_mean) < 1.0:  # Within 1 MW of zero
        print("✅ Raw noise mean is close to zero")
        checks_passed += 1
    else:
        print(f"❌ Raw noise mean too large: {raw_mean:.2f} MW")
    
    # Check 2: Raw noise std should match expected
    total_checks += 1
    if abs(raw_std - expected_std) < expected_std * 0.2:  # Within 20%
        print("✅ Raw noise standard deviation matches expected")
        checks_passed += 1
    else:
        print(f"❌ Raw noise std mismatch: got {raw_std:.2f}, expected {expected_std:.2f}")
    
    # Check 3: Filtered noise should be smoother than raw
    total_checks += 1
    if filtered_roughness < raw_roughness:
        print("✅ Low-pass filter reduces noise roughness")
        checks_passed += 1
    else:
        print("❌ Low-pass filter not working properly")
    
    # Check 4: Final power mean should be close to setpoint
    total_checks += 1
    if abs(final_mean - base_powers[0]) < 1.0:
        print("✅ Final power mean matches setpoint")
        checks_passed += 1
    else:
        print(f"❌ Final power mean drift: {final_mean:.2f} vs {base_powers[0]:.2f}")
    
    # Check 5: No negative powers
    total_checks += 1
    if np.all(final_powers >= 0):
        print("✅ No negative power outputs")
        checks_passed += 1
    else:
        print("❌ Some power outputs are negative")
    
    # Check 6: Reproducibility
    total_checks += 1
    if np.allclose(powers1, powers2, rtol=1e-10):
        print("✅ Reproducible results with same seed")
        checks_passed += 1
    else:
        print("❌ Results not reproducible with same seed")
    
    print(f"\nOverall: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All tests passed! Gaussian white noise implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Check implementation.")
    
    return checks_passed == total_checks


def create_noise_visualization():
    """Create a visualization of the noise behavior"""
    print("\n" + "="*60)
    print("CREATING NOISE VISUALIZATION")
    print("="*60)
    
    try:
        # Create heat source with noise
        heat_source = ConstantHeatSource(
            rated_power_mw=3000.0,
            noise_enabled=True,
            noise_std_percent=0.8,
            noise_seed=42,
            noise_filter_time_constant=20.0
        )
        
        # Run simulation
        dt = 1.0
        duration = 600  # 10 minutes
        time_steps = int(duration / dt)
        
        times = []
        base_powers = []
        final_powers = []
        raw_noise = []
        filtered_noise = []
        
        for i in range(time_steps):
            result = heat_source.update(dt)
            state = heat_source.get_state_dict()
            
            times.append(heat_source.time)
            base_powers.append(state['base_power_mw'])
            final_powers.append(state['thermal_power_mw'])
            raw_noise.append(state['raw_noise_mw'])
            filtered_noise.append(state['filtered_noise_mw'])
        
        # Create plots
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Plot 1: Power output comparison
        axes[0].plot(times, base_powers, 'b-', linewidth=2, label='Base Power (Setpoint)')
        axes[0].plot(times, final_powers, 'r-', linewidth=1, alpha=0.8, label='Final Power (with noise)')
        axes[0].set_ylabel('Power (MW)')
        axes[0].set_title('Reactor Power Output with Gaussian White Noise')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Plot 2: Noise comparison
        axes[1].plot(times, raw_noise, 'gray', linewidth=0.5, alpha=0.7, label='Raw Noise')
        axes[1].plot(times, filtered_noise, 'orange', linewidth=1.5, label='Filtered Noise')
        axes[1].set_ylabel('Noise (MW)')
        axes[1].set_title('Raw vs Filtered Gaussian White Noise')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        # Plot 3: Power variation histogram
        power_variation = np.array(final_powers) - np.array(base_powers)
        axes[2].hist(power_variation, bins=30, alpha=0.7, color='green', edgecolor='black')
        axes[2].set_xlabel('Power Variation (MW)')
        axes[2].set_ylabel('Frequency')
        axes[2].set_title('Distribution of Power Variations')
        axes[2].grid(True, alpha=0.3)
        
        # Add statistics text
        mean_var = np.mean(power_variation)
        std_var = np.std(power_variation)
        axes[2].text(0.02, 0.98, f'Mean: {mean_var:.2f} MW\nStd: {std_var:.2f} MW', 
                    transform=axes[2].transAxes, verticalalignment='top',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        plt.savefig('noise_visualization.png', dpi=150, bbox_inches='tight')
        print("📊 Noise visualization saved as 'noise_visualization.png'")
        
        return True
        
    except ImportError:
        print("📊 Matplotlib not available, skipping visualization")
        return False
    except Exception as e:
        print(f"❌ Error creating visualization: {e}")
        return False


def main():
    """Main test function"""
    try:
        # Run functionality tests
        success = test_noise_functionality()
        
        # Create visualization if possible
        create_noise_visualization()
        
        if success:
            print("\n🎯 SUMMARY: Gaussian white noise implementation completed successfully!")
            print("\nKey features implemented:")
            print("  ✅ Configurable noise level (percentage of power)")
            print("  ✅ Low-pass filtering for realistic behavior")
            print("  ✅ Reproducible results with random seeds")
            print("  ✅ Backward compatibility (noise disabled by default)")
            print("  ✅ Comprehensive state reporting")
            print("  ✅ Statistical validation")
        else:
            print("\n⚠️  Some tests failed. Please review the implementation.")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
