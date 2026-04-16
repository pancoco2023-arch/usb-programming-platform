# ADR-04 – Motor de Ejecución Aislado

## Decisión
Separar el motor de ejecución de código como un componente independiente del backend.

## Motivo
Ejecutar código arbitrario de estudiantes representa un riesgo de seguridad. Aislarlo en un sandbox controlado protege al servidor principal de código malicioso o que consuma recursos excesivos.

## Consecuencias
Requiere diseñar una interfaz de comunicación entre el backend API y el motor de ejecución, pero mejora significativamente la seguridad del sistema.
