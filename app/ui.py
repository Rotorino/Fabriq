"""Streamlit UI for production process simulation."""

import sys
from pathlib import Path
import datetime
import json
import random
from typing import Any
from copy import deepcopy
import textwrap

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import time

from scenario import load_config, build_scenario
from engine.simulator import SimulationEngine
from analytics import calculate_analytics
from reporting import build_report
from visualization.plotly_charts import (
    make_queue_length_chart,
    make_machine_utilization_chart,
    make_batch_time_histogram,
    make_scenario_comparison_chart,
    make_radar_comparison_chart,
    make_performance_chart
)

# Page configuration
st.set_page_config(
    page_title="Fabriq: Production Simulation",
    page_icon="assets/favicon.png",
    layout="wide"
)

# Localization Dictionary
LANGUAGES = {
    "English": {
        "title": "Fabriq: Production Simulation",
        "sidebar_title": "Fabriq",
        "sidebar_section": "Section",
        "sidebar_home": "Home",
        "sidebar_launch": "Launch Simulation",
        "sidebar_results": "Results",
        "sidebar_comparison": "Comparison",
        "hero_title": "Fabriq Engine",
        "hero_subtitle": "Intelligent simulation of production systems of the future",
        "feature_core_title": "Simulation Core",
        "feature_core_desc": "High-precision discrete-event engine. Model queues, breakdowns, and delays in real time.",
        "feature_mgmt_title": "Management",
        "feature_mgmt_desc": "Flexible scenario configuration via JSON or interactive parameters. Full control over every machine.",
        "feature_analytics_title": "Analytics",
        "feature_analytics_desc": "Efficiency metrics (OEE), throughput, and detailed reports for each run.",
        "quick_start_title": "Quick Start (Click to expand)",
        "quick_start_step1": "1. Setup: Go to the Launch Simulation section.",
        "quick_start_step2": "2. Selection: Choose one of the 15 base scenarios.",
        "quick_start_step3": "3. Adjustment: Set the number of batches and equipment reliability.",
        "quick_start_step4": "4. Start: Press the button and watch the 'Matrix'.",
        "quick_start_step5": "5. Analysis: Study radar charts and histograms in the Results tab.",
        "launch_title": "Setup and Launch",
        "base_scenario": "Base Scenario",
        "line_schema": "Production Line Schema",
        "parameters": "Parameters",
        "editor": "Scenario Editor (JSON)",
        "num_batches": "Number of Batches",
        "sim_duration": "Simulation Duration",
        "seed": "Seed",
        "run_button": "Run Simulation",
        "simulating": "Simulating...",
        "done": "Done!",
        "results_title": "Results Analysis",
        "no_results": "No results.",
        "last_run": "Last Run",
        "tab_summary": "Summary",
        "tab_viz": "Visualization",
        "tab_details": "Details",
        "tab_perf": "Performance",
        "tab_history": "Session History",
        "metric_total": "Total",
        "metric_completed": "Completed",
        "metric_rejection": "Rejection",
        "metric_time": "Time",
        "table_stage": "Stage",
        "table_processed": "Processed",
        "table_utilization": "Utilization (%)",
        "table_breakdowns": "Breakdowns",
        "history_empty": "History is empty.",
        "comparison_title": "Strategy Comparison",
        "comparison_button": "Start Analysis",
        "lang_label": "Language",
        "json_error": "JSON format error.",
        "viz_error": "Visualization error.",
        "clear_history": "Clear History",
        "perf_title": "Engine Performance (Processed Events)",
        "perf_x": "Run ID",
        "perf_y": "Event Count",
        "radar_title": "Strategy Efficiency (KPI Radar)",
        "radar_output": "Output",
        "radar_utilization": "Utilization",
        "radar_throughput": "Throughput (x100)",
        "radar_quality": "Quality",
        "metric_output": "Output",
        "metric_utilization": "Avg Utilization (%)",
        "metric_throughput": "Throughput",
        "metric_rejection_val": "Rejection %",
    },
    "Русский": {
        "title": "Fabriq: Симуляция производства",
        "sidebar_title": "Fabriq",
        "sidebar_section": "Раздел",
        "sidebar_home": "Главная",
        "sidebar_launch": "Запуск симуляции",
        "sidebar_results": "Результаты",
        "sidebar_comparison": "Сравнение",
        "hero_title": "Fabriq Engine",
        "hero_subtitle": "Интеллектуальное моделирование производственных систем будущего",
        "feature_core_title": "Ядро симуляции",
        "feature_core_desc": "Дискретно-событийный движок с высокой точностью. Моделируйте очереди, поломки и задержки в реальном времени.",
        "feature_mgmt_title": "Управление",
        "feature_mgmt_desc": "Гибкая настройка сценариев через JSON или интерактивные параметры. Полный контроль над каждой машиной.",
        "feature_analytics_title": "Аналитика",
        "feature_analytics_desc": "Метрики эффективности (OEE), пропускная способность и детализированные отчеты по каждому запуску.",
        "quick_start_title": "Быстрый старт (Нажмите, чтобы развернуть)",
        "quick_start_step1": "1. Настройка: Перейдите в раздел Запуск симуляции.",
        "quick_start_step2": "2. Выбор: Выберите один из 15 базовых сценариев.",
        "quick_start_step3": "3. Корректировка: Настройте количество партий и надежность оборудования.",
        "quick_start_step4": "4. Старт: Нажмите заветную кнопку и наблюдайте за 'Матрицей'.",
        "quick_start_step5": "5. Анализ: Изучите лепестковые диаграммы и гистограммы во вкладке Результаты.",
        "launch_title": "Настройка и запуск",
        "base_scenario": "Базовый сценарий",
        "line_schema": "Схема производственной линии",
        "parameters": "Параметры",
        "editor": "Редактор сценария (JSON)",
        "num_batches": "Количество партий",
        "sim_duration": "Длительность симуляции",
        "seed": "Seed",
        "run_button": "Запустить симуляцию",
        "simulating": "Моделирование...",
        "done": "Готово!",
        "results_title": "Анализ результатов",
        "no_results": "Нет результатов.",
        "last_run": "Последний запуск",
        "tab_summary": "Сводка",
        "tab_viz": "Визуализация",
        "tab_details": "Детальные данные",
        "tab_perf": "Производительность",
        "tab_history": "История сессии",
        "metric_total": "Всего",
        "metric_completed": "Завершено",
        "metric_rejection": "Брак",
        "metric_time": "Время",
        "table_stage": "Этап",
        "table_processed": "Обработано",
        "table_utilization": "Загрузка (%)",
        "table_breakdowns": "Поломок",
        "history_empty": "История пуста.",
        "comparison_title": "Сравнение стратегий",
        "comparison_button": "Начать анализ",
        "lang_label": "Язык",
        "json_error": "Ошибка в формате JSON.",
        "viz_error": "Ошибка визуализации.",
        "clear_history": "Очистить историю",
        "perf_title": "Производительность движка (Обработано событий)",
        "perf_x": "ID запуска",
        "perf_y": "Кол-во событий",
        "radar_title": "Эффективность стратегий (KPI Радар)",
        "radar_output": "Выпуск",
        "radar_utilization": "Загрузка",
        "radar_throughput": "Пропускная (x100)",
        "radar_quality": "Качество",
        "metric_output": "Выпуск (партий)",
        "metric_utilization": "Ср. загрузка (%)",
        "metric_throughput": "Пропускная способность",
        "metric_rejection_val": "% брака",
    }
}

# Constants
SCENARIO_FILES = {
    "Base": "configs/base_scenario.json",
    "High Load": "configs/high_load.json",
    "Frequent Breakdowns": "configs/frequent_breakdowns.json",
    "Bottleneck Entry": "configs/bottleneck_entry.json",
    "Bottleneck Exit": "configs/bottleneck_exit.json",
    "Choke Point": "configs/choke_point.json",
    "Fragile Machines": "configs/fragile_machines.json",
    "Long Repairs": "configs/long_repairs.json",
    "Stable Line": "configs/stable_line.json",
    "Parallel Processing": "configs/parallel_processing.json",
    "Buffer Stress": "configs/buffer_stress.json",
    "Variable Routing": "configs/variable_routing.json",
    "Massive Batch Load": "configs/massive_batch_load.json",
    "Extended Duration": "configs/extended_duration.json",
    "Zero Buffer Rejection": "configs/zero_buffer_rejection.json",
}

def run_simulation(config: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Apply overrides to config and run simulation."""
    if "batches_count" in overrides:
        config["batches"]["count"] = overrides["batches_count"]
    if "simulation_duration" in overrides:
        config["simulation_duration"] = overrides["simulation_duration"]
    if "seed" in overrides:
        config["seed"] = overrides["seed"]
    if "breakdown_probability" in overrides:
        prob = overrides["breakdown_probability"] / 100.0
        for stage in config.get("stages", []):
            for machine in stage.get("machines", []):
                machine["breakdown_probability"] = prob

    scenario_input = build_scenario(config)
    rng_seed = overrides.get("seed") or scenario_input.scenario_config.seed
    
    engine = SimulationEngine(
        production_line=scenario_input.production_line,
        batches=scenario_input.batches,
        simulation_duration=scenario_input.scenario_config.simulation_duration,
        scenario_name=scenario_input.scenario_config.name,
        rng=random.Random(rng_seed),
    )
    
    result = engine.run()
    analytics = calculate_analytics(result)
    
    return {
        "result": result,
        "analytics": analytics,
        "config": scenario_input.scenario_config,
        "raw_config": config
    }

def render_line_graph(config: dict[str, Any]) -> str:
    """Generate DOT description of the production line."""
    dot = "digraph {\n"
    dot += '  rankdir=LR;\n'
    dot += '  node [shape=rectangle, style="filled,rounded", color="#E1F5FE", fontname="Arial", fontsize=10];\n'
    dot += '  edge [color="#546E7A", arrowhead=vee];\n'
    
    stages = config.get("stages", [])
    for stage in stages:
        s_id = stage.get("stage_id", "Unknown")
        s_name = stage.get("name", s_id)
        m_count = len(stage.get("machines", []))
        dot += f'  "{s_id}" [label="{s_name}\\n({m_count} machines)"];\n'
        
    for stage in stages:
        s_id = stage.get("stage_id")
        n_id = stage.get("next_stage_id")
        if n_id:
            dot += f'  "{s_id}" -> "{n_id}";\n'
    dot += "}"
    return dot

def show_home_page(t: dict[str, str]):
    # Custom CSS for modern UI and animations
    st.markdown(textwrap.dedent(f"""
        <style>
        .factory-container {{
            background: #1b1a28;
            border-radius: 20px;
            padding: 40px;
            position: relative;
            overflow: hidden;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        
        .factory-scene-wrapper {{
            width: 100%;
            height: 380px;
            display: flex;
            justify-content: center;
            align-items: center;
            border-radius: 15px;
            margin-bottom: 25px;
            overflow: hidden;
        }}

        .title-gradient {{
            background: linear-gradient(90deg, #6c63ff, #32e0c4);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 3rem !important;
            margin-top: 0;
            margin-bottom: 10px;
        }}
        
        .hero-description {{
            font-size: 1.2rem;
            color: #a0a0c0;
            margin-bottom: 0;
        }}

        .feature-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            min-height: 250px;
            height: 250px;
            display: flex;
            flex-direction: column;
        }}
        </style>
        <div class="factory-container">
        <div class="factory-scene-wrapper">
        <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 800 400" width="150%" height="150%" preserveAspectRatio="xMidYMid meet">
        <defs>
        <pattern id="floor" x="0" y="0" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="#1b1a28"/><path d="M0 40 L40 0" stroke="#1b1a28" stroke-width="1"/></pattern>
        <linearGradient id="metal" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#4a5568"/><stop offset="30%" stop-color="#718096"/><stop offset="50%" stop-color="#a0aec0"/><stop offset="70%" stop-color="#718096"/><stop offset="100%" stop-color="#2d3748"/></linearGradient>
        <linearGradient id="metal-dark" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#2d3748"/><stop offset="50%" stop-color="#4a5568"/><stop offset="100%" stop-color="#1a202c"/></linearGradient>
        <linearGradient id="belt" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#2d3748"/><stop offset="20%" stop-color="#1a202c"/><stop offset="50%" stop-color="#4a5568"/><stop offset="80%" stop-color="#1a202c"/><stop offset="100%" stop-color="#2d3748"/></linearGradient>
        <radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#00f5d4" stop-opacity="0.6"/><stop offset="50%" stop-color="#00bbf9" stop-opacity="0.2"/><stop offset="100%" stop-color="#9b5de5" stop-opacity="0"/></radialGradient>
        <filter id="blur-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>
        <g id="product-shape">
        <circle cx="0" cy="0" r="28" fill="url(#glow)" filter="url(#blur-glow)" opacity="0.5"><animate attributeName="opacity" values="0.3;0.7;0.3" dur="2s" repeatCount="indefinite"/></circle>
        <rect x="-20" y="-25" width="40" height="50" rx="6" fill="#0f172a" stroke="#00f5d4" stroke-width="1.5"/>
        <clipPath id="product-clip"><rect x="-18" y="-23" width="36" height="46" rx="5"/></clipPath>
        <image xlink:href="https://i.postimg.cc/YL1rmWCy/image.png" x="-18" y="-23" width="36" height="46" preserveAspectRatio="xMidYMid slice" clip-path="url(#product-clip)" opacity="0.95"/>
        <rect x="-18" y="-23" width="36" height="46" rx="5" fill="none" stroke="#00f5d4" stroke-width="1" opacity="0.6"/>
        <circle cx="-15" cy="-20" r="2" fill="#00f5d4" opacity="0.8"><animate attributeName="opacity" values="0.4;1;0.4" dur="1.5s" repeatCount="indefinite"/></circle>
        <circle cx="15" cy="-20" r="2" fill="#00f5d4" opacity="0.8"><animate attributeName="opacity" values="0.4;1;0.4" dur="1.5s" begin="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="-15" cy="20" r="2" fill="#00f5d4" opacity="0.8"><animate attributeName="opacity" values="0.4;1;0.4" dur="1.5s" begin="1s" repeatCount="indefinite"/></circle>
        <circle cx="15" cy="20" r="2" fill="#00f5d4" opacity="0.8"><animate attributeName="opacity" values="0.4;1;0.4" dur="1.5s" begin="1.5s" repeatCount="indefinite"/></circle>
        <rect x="-22" y="-12" width="3" height="24" rx="1" fill="#4a5568"/><rect x="19" y="-12" width="3" height="24" rx="1" fill="#4a5568"/>
        </g>
        </defs>
        <rect width="800" height="400" fill="#1c1b2a"/>
        <ellipse cx="250" cy="340" rx="120" ry="15" fill="#000" opacity="0.4"/>
        <g id="machine">
        <rect x="130" y="120" width="140" height="200" rx="8" fill="url(#metal)" stroke="#2d3748" stroke-width="2"/>
        <rect x="140" y="100" width="120" height="30" rx="5" fill="url(#metal-dark)" stroke="#4a5568" stroke-width="1"/>
        <rect x="135" y="130" width="130" height="180" rx="4" fill="none" stroke="#4a5568" stroke-width="1" opacity="0.5"/>
        <g opacity="0.6"><rect x="150" y="140" width="100" height="3" rx="1" fill="#1a202c"/><rect x="150" y="148" width="100" height="3" rx="1" fill="#1a202c"/><rect x="150" y="156" width="100" height="3" rx="1" fill="#1a202c"/><rect x="150" y="164" width="100" height="3" rx="1" fill="#1a202c"/><rect x="150" y="172" width="100" height="3" rx="1" fill="#1a202c"/></g>
        <rect x="150" y="200" width="100" height="80" rx="4" fill="#1a202c" stroke="#4a5568" stroke-width="1"/>
        <rect x="160" y="210" width="80" height="40" rx="2" fill="#0f172a" stroke="#00f5d4" stroke-width="1"/>
        <rect x="165" y="218" width="20" height="4" rx="1" fill="#00f5d4" opacity="0.8"><animate attributeName="width" values="20;50;20" dur="2s" repeatCount="indefinite"/></rect>
        <rect x="165" y="228" width="40" height="4" rx="1" fill="#00bbf9" opacity="0.6"><animate attributeName="width" values="40;70;40" dur="2.5s" repeatCount="indefinite"/></rect>
        <rect x="165" y="238" width="30" height="4" rx="1" fill="#9b5de5" opacity="0.5"><animate attributeName="width" values="30;60;30" dur="3s" repeatCount="indefinite"/></rect>
        <circle cx="170" cy="265" r="5" fill="#ef4444" opacity="0.8"><animate attributeName="opacity" values="0.5;1;0.5" dur="1s" repeatCount="indefinite"/></circle>
        <circle cx="190" cy="265" r="5" fill="#22c55e" opacity="0.8"/><circle cx="210" cy="265" r="5" fill="#3b82f6" opacity="0.8"/><circle cx="230" cy="265" r="5" fill="#eab308" opacity="0.8"/>
        <circle cx="200" cy="115" r="6" fill="#22c55e"><animate attributeName="opacity" values="1;0.3;1" dur="1.2s" repeatCount="indefinite"/></circle>
        <rect x="260" y="240" width="40" height="50" rx="4" fill="url(#metal-dark)" stroke="#4a5568" stroke-width="2"/>
        <rect x="265" y="245" width="30" height="40" rx="2" fill="#1a202c"/><rect x="295" y="238" width="8" height="54" rx="2" fill="#4a5568"/>
        <rect x="180" y="80" width="40" height="40" rx="4" fill="url(#metal)" stroke="#2d3748" stroke-width="2"><animateTransform attributeName="transform" type="translate" values="0,0; 0,30; 0,0" dur="1.5s" repeatCount="indefinite"/></rect>
        <rect x="195" y="60" width="10" height="25" fill="#718096"><animateTransform attributeName="transform" type="translate" values="0,0; 0,30; 0,0" dur="1.5s" repeatCount="indefinite"/></rect>
        <rect x="140" y="320" width="120" height="20" rx="2" fill="#2d3748"/><rect x="150" y="340" width="15" height="15" rx="2" fill="#1a202c"/><rect x="235" y="340" width="15" height="15" rx="2" fill="#1a202c"/>
        </g>
        <rect x="350" y="310" width="12" height="50" fill="#4a5568"/><rect x="450" y="310" width="12" height="50" fill="#4a5568"/><rect x="550" y="310" width="12" height="50" fill="#4a5568"/><rect x="650" y="310" width="12" height="50" fill="#4a5568"/>
        <rect x="300" y="290" width="400" height="20" rx="4" fill="#1a202c" stroke="#4a5568" stroke-width="1"/>
        <rect x="300" y="265" width="400" height="25" fill="url(#belt)" stroke="#2d3748" stroke-width="1"/>
        <g opacity="0.3"><rect x="0" y="268" width="30" height="3" rx="1" fill="#718096"><animateTransform attributeName="transform" type="translate" from="300,0" to="700,0" dur="3s" repeatCount="indefinite"/></rect><rect x="0" y="275" width="40" height="3" rx="1" fill="#718096"><animateTransform attributeName="transform" type="translate" from="300,0" to="700,0" dur="3s" begin="1s" repeatCount="indefinite"/></rect><rect x="0" y="282" width="25" height="3" rx="1" fill="#718096"><animateTransform attributeName="transform" type="translate" from="300,0" to="700,0" dur="3s" begin="2s" repeatCount="indefinite"/></rect></g>
        <g>
        <circle cx="320" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 320 290" to="360 320 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="380" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 380 290" to="360 380 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="440" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 440 290" to="360 440 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="500" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 500 290" to="360 500 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="560" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 560 290" to="360 560 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="620" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 620 290" to="360 620 290" dur="0.5s" repeatCount="indefinite"/></circle>
        <circle cx="680" cy="290" r="8" fill="#4a5568" stroke="#2d3748" stroke-width="1"><animateTransform attributeName="transform" type="rotate" from="0 680 290" to="360 680 290" dur="0.5s" repeatCount="indefinite"/></circle>
        </g>
        <g><animateTransform attributeName="transform" type="translate" from="320,245" to="720,245" dur="6s" repeatCount="indefinite"/><use href="#product-shape"/></g>
        <g><animateTransform attributeName="transform" type="translate" from="320,245" to="720,245" dur="6s" begin="2s" repeatCount="indefinite"/><use href="#product-shape"/></g>
        <g><animateTransform attributeName="transform" type="translate" from="320,245" to="720,245" dur="6s" begin="4s" repeatCount="indefinite"/><use href="#product-shape"/></g>
        <g><circle cx="305" cy="250" r="3" fill="#00f5d4" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="1.5s" repeatCount="indefinite"/><animate attributeName="cy" values="250;225" dur="1.5s" repeatCount="indefinite"/><animate attributeName="cx" values="305;290" dur="1.5s" repeatCount="indefinite"/></circle><circle cx="305" cy="255" r="2" fill="#00bbf9" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="1.5s" begin="0.3s" repeatCount="indefinite"/><animate attributeName="cy" values="255;230" dur="1.5s" begin="0.3s" repeatCount="indefinite"/><animate attributeName="cx" values="305;315" dur="1.5s" begin="0.3s" repeatCount="indefinite"/></circle><circle cx="305" cy="245" r="2.5" fill="#9b5de5" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="1.5s" begin="0.6s" repeatCount="indefinite"/><animate attributeName="cy" values="245;220" dur="1.5s" begin="0.6s" repeatCount="indefinite"/><animate attributeName="cx" values="305;300" dur="1.5s" begin="0.6s" repeatCount="indefinite"/></circle></g>
        <g id="box"><ellipse cx="740" cy="345" rx="45" ry="10" fill="#000" opacity="0.3"/><rect x="700" y="280" width="80" height="60" rx="4" fill="#2d3748" stroke="#4a5568" stroke-width="2"/><rect x="705" y="285" width="70" height="50" rx="2" fill="#1a202c"/><rect x="700" y="280" width="80" height="60" rx="4" fill="none" stroke="#4a5568" stroke-width="2" stroke-dasharray="4,2"/><rect x="715" y="295" width="50" height="20" rx="2" fill="#0f172a" stroke="#00f5d4" stroke-width="1"/><path d="M735 318 L740 328 L745 318" fill="none" stroke="#00f5d4" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><animate attributeName="opacity" values="1;0.3;1" dur="1s" repeatCount="indefinite"/></path></g>
        <path d="M130 250 Q 100 250, 100 300 Q 100 350, 80 350" fill="none" stroke="#4a5568" stroke-width="3" stroke-linecap="round"/><path d="M130 270 Q 110 270, 110 310 Q 110 360, 90 360" fill="none" stroke="#2d3748" stroke-width="2" stroke-linecap="round"/><circle cx="80" cy="350" r="5" fill="#1a202c" stroke="#4a5568" stroke-width="1"/><circle cx="90" cy="360" r="4" fill="#1a202c" stroke="#4a5568" stroke-width="1"/><rect x="150" y="70" width="100" height="8" rx="4" fill="#4a5568"/><rect x="180" y="50" width="8" height="25" rx="4" fill="#4a5568"/><circle cx="184" cy="48" r="6" fill="#ef4444" opacity="0.7"><animate attributeName="opacity" values="0.5;1;0.5" dur="2s" repeatCount="indefinite"/></circle><circle cx="184" cy="35" r="8" fill="#718096" opacity="0"><animate attributeName="opacity" values="0;0.4;0" dur="3s" repeatCount="indefinite"/><animate attributeName="cy" values="35;10" dur="3s" repeatCount="indefinite"/><animate attributeName="r" values="8;15" dur="3s" repeatCount="indefinite"/></circle><circle cx="190" cy="30" r="6" fill="#a0aec0" opacity="0"><animate attributeName="opacity" values="0;0.3;0" dur="3s" begin="1s" repeatCount="indefinite"/><animate attributeName="cy" values="30;5" dur="3s" begin="1s" repeatCount="indefinite"/><animate attributeName="r" values="6;12" dur="3s" begin="1s" repeatCount="indefinite"/></circle>
        <g transform="translate(680, 375)"><rect x="0" y="0" width="8" height="8" rx="2" fill="#22c55e"><animate attributeName="opacity" values="1;0.3;1" dur="0.8s" repeatCount="indefinite"/></rect><rect x="12" y="0" width="8" height="8" rx="2" fill="#3b82f6"/><rect x="24" y="0" width="8" height="8" rx="2" fill="#eab308"/><rect x="36" y="0" width="8" height="8" rx="2" fill="#ef4444"/></g>
        </svg>
        </div>
        <h1 class="title-gradient">{t['hero_title']}</h1>
        <p class="hero-description">{t['hero_subtitle']}</p>
        </div>
        """), unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(textwrap.dedent(f"""
            <div class="feature-card">
                <h3 style="color: #6c63ff;">{t['feature_core_title']}</h3>
                <p style="color: #d1d1e0;">{t['feature_core_desc']}</p>
            </div>
            """), unsafe_allow_html=True)
    with col2:
        st.markdown(textwrap.dedent(f"""
            <div class="feature-card">
                <h3 style="color: #32e0c4;">{t['feature_mgmt_title']}</h3>
                <p style="color: #d1d1e0;">{t['feature_mgmt_desc']}</p>
            </div>
            """), unsafe_allow_html=True)
    with col3:
        st.markdown(textwrap.dedent(f"""
            <div class="feature-card">
                <h3 style="color: #ffaa00;">{t['feature_analytics_title']}</h3>
                <p style="color: #d1d1e0;">{t['feature_analytics_desc']}</p>
            </div>
            """), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(t['quick_start_title']):
        st.markdown(textwrap.dedent(f"""
            1. **{t['sidebar_launch']}**: {t['quick_start_step1']}
            2. **{t['base_scenario']}**: {t['quick_start_step2']}
            3. **{t['parameters']}**: {t['quick_start_step3']}
            4. **{t['run_button']}**: {t['quick_start_step4']}
            5. **{t['sidebar_results']}**: {t['quick_start_step5']}
            """))

def main():
    if "simulation_history" not in st.session_state:
        st.session_state["simulation_history"] = []

    st.sidebar.image("assets/favicon.png", width=80)
    st.sidebar.title("Fabriq")
    
    # Language Selector
    lang = st.sidebar.selectbox("Language / Язык", list(LANGUAGES.keys()), index=0)
    t = LANGUAGES[lang]

    page = st.sidebar.radio(
        t["sidebar_section"],
        [t["sidebar_home"], t["sidebar_launch"], t["sidebar_results"], t["sidebar_comparison"]],
        help="Navigation through the main sections of the application."
    )

    if page == t["sidebar_home"]:
        show_home_page(t)
    elif page == t["sidebar_launch"]:
        show_launch_page(t)
    elif page == t["sidebar_results"]:
        show_results_page(t)
    elif page == t["sidebar_comparison"]:
        show_comparison_page(t)

def show_matrix_effect():
    """Display a colorful, high-tech 'Matrix' progress effect."""
    matrix_container = st.empty()
    colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"]
    for i in range(15):
        color = colors[i % len(colors)]
        random_nums = "".join([str(random.randint(0, 9)) for _ in range(50)])
        matrix_container.markdown(f"<div style='font-family: monospace; color: {color}; text-shadow: 0 0 5px {color}; overflow: hidden; white-space: nowrap; height: 25px;'>{random_nums}</div>", unsafe_allow_html=True)
        time.sleep(0.05)
    matrix_container.empty()

def show_launch_page(t: dict[str, str]):
    st.title(t["launch_title"])
    col_sel, col_viz = st.columns([1, 2])
    with col_sel:
        scenario_label = st.selectbox(t["base_scenario"], list(SCENARIO_FILES.keys()))
        if "editing_config" not in st.session_state or st.session_state.get("current_scenario_label") != scenario_label:
            st.session_state["editing_config"] = load_config(SCENARIO_FILES[scenario_label])
            st.session_state["current_scenario_label"] = scenario_label
    with col_viz:
        st.markdown(f"##### {t['line_schema']}")
        try:
            st.graphviz_chart(render_line_graph(st.session_state["editing_config"]))
        except:
            st.error(t["viz_error"])

    tab_params, tab_editor = st.tabs([t["parameters"], t["editor"]])
    with tab_params:
        col1, col2 = st.columns(2)
        config = st.session_state["editing_config"]
        with col1:
            num_batches = st.slider(t["num_batches"], 5, 500, config.get("batches", {}).get("count", 50), 5)
            sim_duration = st.slider(t["sim_duration"], 10, 5000, int(config.get("simulation_duration", 1000)), 10)
        with col2:
            seed = st.number_input(t["seed"], 0, 99999, config.get("seed", 42))

    with tab_editor:
        config_str = json.dumps(st.session_state["editing_config"], indent=2, ensure_ascii=False)
        new_config_str = st.text_area(t["editor"], config_str, 350)
        try:
            st.session_state["editing_config"] = json.loads(new_config_str)
        except:
            st.error(t["json_error"])

    if st.button(t["run_button"], type="primary", width='stretch'):
        with st.spinner(t["simulating"]):
            try:
                overrides = {"batches_count": num_batches, "simulation_duration": float(sim_duration), "seed": seed}
                show_matrix_effect()
                output = run_simulation(deepcopy(st.session_state["editing_config"]), overrides)
                st.session_state.update({"last_result": output["result"], "last_analytics": output["analytics"], "last_scenario": scenario_label, "last_config": output["config"]})
                st.session_state["simulation_history"].append({"id": len(st.session_state["simulation_history"]) + 1, "timestamp": datetime.datetime.now().strftime("%H:%M:%S"), "scenario": scenario_label, "analytics": output["analytics"], "result": output["result"], "config": output["config"]})
                st.success(t["done"])
            except Exception as e:
                st.error(f"Error: {e}")

def show_results_page(t: dict[str, str]):
    st.title(t["results_title"])
    if "last_result" not in st.session_state:
        st.warning(t["no_results"])
        if st.session_state.get("simulation_history") and st.button(t["last_run"]):
            last = st.session_state["simulation_history"][-1]
            st.session_state.update({"last_result": last["result"], "last_analytics": last["analytics"], "last_scenario": last["scenario"], "last_config": last["config"]})
            st.rerun()
        st.stop()
    tab_summary, tab_charts, tab_tables, tab_perf, tab_history = st.tabs([t["tab_summary"], t["tab_viz"], t["tab_details"], t["tab_perf"], t["tab_history"]])
    result, analytics, config = st.session_state["last_result"], st.session_state["last_analytics"], st.session_state["last_config"]
    with tab_summary:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(t["metric_total"], analytics.general.total_batches)
        m2.metric(t["metric_completed"], analytics.general.completed_batches)
        m3.metric(t["metric_rejection"], f"{analytics.general.rejection_rate*100:.1f}%")
        m4.metric(t["metric_time"], f"{analytics.general.simulation_time:.1f}")
    with tab_charts:
        st.plotly_chart(make_queue_length_chart(result), width='stretch')
        c1, c2 = st.columns(2)
        c1.plotly_chart(make_machine_utilization_chart(analytics.machines), width='stretch')
        c2.plotly_chart(make_batch_time_histogram(analytics.batches), width='stretch')
    with tab_tables:
        st.dataframe(pd.DataFrame([{t["table_stage"]: m.stage_id, t["table_processed"]: m.processed_batches, t["table_utilization"]: f"{m.utilization * 100:.1f}%"} for m in analytics.stages]), width='stretch')
        st.dataframe(pd.DataFrame([{"ID": m.machine_id, t["table_utilization"]: f"{m.utilization * 100:.1f}%", t["table_breakdowns"]: m.breakdowns} for m in analytics.machines]), width='stretch')
    with tab_perf:
        st.plotly_chart(make_performance_chart(st.session_state["simulation_history"], t), width='stretch')
    with tab_history:
        show_history_view(t)

def show_history_view(t: dict[str, str]):
    history = st.session_state.get("simulation_history", [])
    if not history:
        st.info(t["history_empty"])
        return
    h_data = [{"ID": e["id"], "Time": e["timestamp"], "Scenario": e["scenario"], "Output": e["analytics"].general.completed_batches} for e in history]
    st.dataframe(pd.DataFrame(h_data).sort_values("ID", ascending=False), width='stretch', hide_index=True)
    if st.button(t["clear_history"]):
        st.session_state["simulation_history"] = []
        st.rerun()

def show_comparison_page(t: dict[str, str]):
    st.title(t["comparison_title"])
    if st.button(t["comparison_button"], type="primary", width='stretch'):
        results = {}
        for name, path in SCENARIO_FILES.items():
            out = run_simulation(load_config(path), {})
            results[name] = {
                t["metric_output"]: out["analytics"].general.completed_batches, 
                t["metric_rejection_val"]: round(out["analytics"].general.rejection_rate * 100, 1), 
                t["metric_utilization"]: round(sum(m.utilization for m in out["analytics"].machines)/len(out["analytics"].machines)*100, 1) if out["analytics"].machines else 0, 
                t["metric_throughput"]: round(out["analytics"].general.throughput, 2)
            }
        st.session_state["global_comparison"] = results
    if "global_comparison" in st.session_state:
        data = st.session_state["global_comparison"]
        c1, c2 = st.columns(2)
        c1.plotly_chart(make_scenario_comparison_chart(data), width='stretch')
        c2.plotly_chart(make_radar_comparison_chart(data, t), width='stretch')
        st.dataframe(pd.DataFrame(data).T, width='stretch')

if __name__ == "__main__":
    main()
