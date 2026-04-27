"""
TEST DEL SISTEMA ARTHUR
=======================
Ejecuta para verificar que todo funciona.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test(name, func):
    try:
        result = func()
        print(f"[OK] {name}: {result}")
        return True
    except Exception as e:
        print(f"[FAIL] {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("TESTEANDO SISTEMA ARTHUR")
    print("=" * 60)
    
    results = []
    
    # 1. API
    print("\n1. API...")
    results.append(test("API", lambda: requests.get(f"{BASE_URL}/").json()))
    
    # 2. Modos
    print("\n2. Modos Arthur...")
    results.append(test("Modes", lambda: requests.get(f"{BASE_URL}/api/v1/arthur/modes").json()))
    
    # 3. Health
    print("\n3. Health...")
    results.append(test("Health", lambda: requests.get(f"{BASE_URL}/api/v1/arthur/health").json()))
    
    # 4. Simulation
    print("\n4. Simulation...")
    results.append(test("SimStats", lambda: requests.get(f"{BASE_URL}/api/v1/simulation/simulation-stats").json()))
    
    # 5. Chatbot pregunta 1
    print("\n5. Test Chatbot pregunta 1...")
    response = requests.post(
        f"{BASE_URL}/api/v1/arthur/query",
        json={"question": "Como se gana en Dune?"},
        timeout=90
    )
    if response.status_code == 200:
        data = response.json()
        answer = data.get("answer", "")
        print(f"   Respuesta: {len(answer)} chars")
        print(f"   Preview: {answer[:100]}...")
        results.append(len(answer) > 20)
    else:
        results.append(False)
    
    # 6. Chatbot pregunta 2
    print("\n6. Test Chatbot pregunta 2...")
    response2 = requests.post(
        f"{BASE_URL}/api/v1/arthur/query",
        json={"question": "Que unidades tiene House Atreides?"},
        timeout=90
    )
    if response2.status_code == 200:
        data2 = response2.json()
        answer2 = data2.get("answer", "")
        print(f"   Respuesta: {len(answer2)} chars")
        results.append(len(answer2) > 20)
    else:
        results.append(False)
    
    # 7. Simulacion
    print("\n7. Ejecutar simulacion...")
    sim_response = requests.post(
        f"{BASE_URL}/api/v1/simulation/simulate",
        json={"faction": "Atreides", "games": 3},
        timeout=60
    )
    if sim_response.status_code == 200:
        sim_data = sim_response.json()
        winners = [g.get("winner") for g in sim_data]
        print(f"   Games: {len(sim_data)}, Ganadores: {winners}")
        results.append(True)
    else:
        results.append(False)
    
    # 8. Stats finales
    print("\n8. Stats finales...")
    stats = requests.get(f"{BASE_URL}/api/v1/simulation/simulation-stats").json()
    print(f"   Games played: {stats.get('games_played', 0)}")
    results.append(True)
    
    # Resumen
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTADO: {passed}/{total} tests pasados")
    
    if passed == total:
        print("[OK] TODO FUNCIONA!")
    else:
        print(f"[WARN] {total - passed} fallaron")
    
    print("\nChatbot: http://localhost:7860")

if __name__ == "__main__":
    main()