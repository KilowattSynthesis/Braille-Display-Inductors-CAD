from machine import Pin
import time

# Pin definitions for shift register control
PIN_SHIFT_SER_IN = Pin(2, Pin.OUT)    # GP2: Serial data input
PIN_SHIFT_SRCK = Pin(3, Pin.OUT)      # GP3: Shift register clock
PIN_SHIFT_N_SRCLR = Pin(4, Pin.OUT)   # GP4: Shift register clear
PIN_SHIFT_RCLK = Pin(5, Pin.OUT)      # GP5: Register clock (latch)
PIN_SHIFT_N_OE = Pin(6, Pin.OUT)      # GP6: Output enable


def init_shift_register() -> None:
    """Initialize shift register pins to default states."""
    # Clear shift register.
    PIN_SHIFT_N_SRCLR.value(0)
    time.sleep(0.1)
    PIN_SHIFT_N_SRCLR.value(1) # Active low, so set to normal (not clearing).
    time.sleep(0.1)

    PIN_SHIFT_N_OE.value(0)     # Active low, set low to enable outputs
    PIN_SHIFT_SRCK.value(0)   # Clock starts low
    PIN_SHIFT_RCLK.value(0)   # Latch starts low
    time.sleep(0.1)           # Wait for initialization to complete


def set_shift_registers(data: list[bool], *, delay_time_sec: float = 0.001) -> None:
    """
    Set the state of all shift registers based on input data.
    
    Args:
        data: list of 48 boolean values representing desired output states
             (6 registers x 8 bits per register)
    """
    if len(data) != 48:
        raise ValueError("Data must contain exactly 48 boolean values")
    
    # Shift out all 48 bits
    for bit in reversed(data):  # Shift MSB first
        # Set data bit.
        PIN_SHIFT_SER_IN.value(1 if bit else 0)
        time.sleep(delay_time_sec)
        
        # Clock in the bit.
        PIN_SHIFT_SRCK.value(1)
        time.sleep(delay_time_sec)
        PIN_SHIFT_SRCK.value(0)
        time.sleep(delay_time_sec)
    
    # Latch the data to outputs
    PIN_SHIFT_RCLK.value(1)
    time.sleep(delay_time_sec)
    PIN_SHIFT_RCLK.value(0)
    time.sleep(delay_time_sec)

def basic_demo() -> None:
    print("All outputs off (high-impedance)")
    outputs = [False] * 48  # All outputs off
    set_shift_registers(outputs)
    time.sleep(2)

    print("All outputs on - positive")
    outputs = [(i % 2 == 0) for i in range(48)]  # Alternating on/off pattern
    set_shift_registers(outputs)
    time.sleep(2)

    print("All outputs on - negative")
    outputs = [(i % 2 == 1) for i in range(48)]  # Alternating on/off pattern
    set_shift_registers(outputs)
    time.sleep(2)


def make_shift_register_state_single_dot(*, cell_number: int, dot_number: int, state: str) -> list[bool]:
    """

    The AD116 is high-impedance when `IN_A = IN_B = 0`, and brake when `IN_A = IN_B = 1`.

    Args:
        cell_number: The cell number (0-3).
        dot_number: The dot number (1-6).
        state: Literal["brake", "high-z", "pos", "neg"]
    """

    # Initialize all dots to high-z.
    shift_register_state = [False] * 48

    # Map the state.
    in_a_in_b = {
        "brake": (True, True),
        "high-z": (False, False),
        "pos": (True, False),
        "neg": (False, True)
    }[state]

    # Set the state of the dot.
    base_offset = cell_number * 6*2 + (dot_number-1) * 2
    shift_register_state[base_offset] = in_a_in_b[0]
    shift_register_state[base_offset + 1] = in_a_in_b[1]

    return shift_register_state


def braille_demo() -> None:
    """Loop through each dot in each cells, and display it."""

    for cell_number in range(4):
        for dot_number in (1, 2, 3, 4, 5, 6):
            # for state in ("brake", "high-z", "pos", "neg"):
            for state in ("brake", "pos", "neg"):
                print(f"Cell {cell_number}, Dot {dot_number}, State {state}")
                shift_register_state = make_shift_register_state_single_dot(
                    cell_number=cell_number, dot_number=dot_number, state=state
                )
                set_shift_registers(shift_register_state)
                time.sleep(1.5)


def main() -> None:
    print("Starting init.")
    init_shift_register()
    print("Init complete.")

    print("Starting basic demo.")
    basic_demo()
    print("Basic demo complete.")

    print("Starting braille demo.")
    braille_demo()
    print("Braille demo complete.")

while True:
    main()
