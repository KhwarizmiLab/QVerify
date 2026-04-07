import random

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from qverify_simulation.simulation.backend import sim_circuits


def measure_cir(circuit, qr, cr, bit):
    circuit.measure(qr[bit], cr[bit])
    return circuit


def base_B2_A3(basisB3, qr, bit):
    return basisB3


def base_A1(basisB1, qr, bit):
    basisB1.h(qr[bit])
    return basisB1


def base_A2_B1(basisB2, qr, bit):
    basisB2.s(qr[bit])
    basisB2.h(qr[bit])
    basisB2.t(qr[bit])
    basisB2.h(qr[bit])
    return basisB2


def base_B3(basisB4, qr, bit):
    basisB4.s(qr[bit])
    basisB4.h(qr[bit])
    basisB4.tdg(qr[bit])
    basisB4.h(qr[bit])
    return basisB4


entanglment_basis_mapA = {1: base_A1, 2: base_A2_B1, 3: base_B2_A3}
entanglment_basis_mapB = {1: base_A2_B1, 2: base_B2_A3, 3: base_B3}


def apply_basis(num_qubits, qc, qrA, qrB, alice_basis, bob_basis):
    for i in range(num_qubits):
        qc = entanglment_basis_mapA[alice_basis[i]](qc, qrA, i)
    for i in range(num_qubits):
        qc = entanglment_basis_mapB[bob_basis[i]](qc, qrB, i)
    qc.barrier(label="Basis")
    return qc


def apply_basis_Eve(num_qubits, qc, qrA, qrB, user_basis):
    for i in range(num_qubits):
        qc = entanglment_basis_mapA[user_basis[i]](qc, qrA, i)
    for i in range(num_qubits):
        qc = entanglment_basis_mapA[user_basis[i]](qc, qrB, i)
    qc.barrier(label="Basis")
    return qc


def apply_measurement(num_qubits, qc, qrA, qrB, crA, crB):
    for i in range(num_qubits):
        qc = measure_cir(qc, qrA, crA, i)
        qc = measure_cir(qc, qrB, crB, i)
    qc.barrier(label="Measure")
    return qc


def get_result(qc):
    res = sim_circuits(qc, shots=1)
    results = list(res)[0][::-1].split(" ")
    return results[0], results[1]


def create_singlets(num_qubits):
    qrA = QuantumRegister(num_qubits, name="qrA")
    qrB = QuantumRegister(num_qubits, name="qrB")
    crA = ClassicalRegister(num_qubits, name="crA")
    crB = ClassicalRegister(num_qubits, name="crB")
    qc = QuantumCircuit(qrA, qrB, crA, crB)
    qc.x(qrA)
    qc.x(qrB)
    qc.h(qrA)
    qc.cx(qrA, qrB)
    qc.barrier(label="singlets_end")
    return qc, qrA, qrB, crA, crB


def alice_measurement_choices(num_qubits):
    return [random.choice([1, 2, 3]) for _ in range(num_qubits)]


def bob_measurement_choices(num_qubits):
    return [random.choice([1, 2, 3]) for _ in range(num_qubits)]


def eve_encode(num_qubits, BA, RE):
    qr2 = QuantumRegister(num_qubits, name="qr2")
    crB2 = ClassicalRegister(num_qubits, name="crB2")
    quantum_channel = QuantumCircuit(qr2, crB2)
    for i in range(num_qubits):
        if RE[i] == 1 or RE[i] == "1":
            quantum_channel.x(qr2[i])
    for i in range(num_qubits):
        quantum_channel = entanglment_basis_mapA[BA[i]](quantum_channel, qr2, i)
    quantum_channel.barrier(qr2, label="AliceSending")
    return qr2, crB2, quantum_channel
