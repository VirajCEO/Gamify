This `requirements.md` is designed to provide a developer with a clear roadmap for building a high-dopamine, AI-driven gamification engine. It focuses on the **logic of the LLM**, the **psychology of the rewards**, and the **simplicity of the user interface**.

***

# Requirements Document: Project "LEVEL UP" (PoC)

## 1. Project Overview
The goal is to build a standalone web application that gamifies daily productivity using a Large Language Model (LLM) as the "Game Master." The system translates high-level user goals into daily actionable quests, tracks progress through a classic RPG stat system (INT, DEX, CHA, VIT), and utilizes "juicy" UI elements to trigger dopamine release and habit formation.

---

## 2. Core Systems & Logic

### 2.1 Persona System
Users select a "Persona" upon setup which dictates how the AI generates tasks and weights rewards.
* **The Visionary:** High focus on Strategy and Networking (CHA/INT).
* **The Operator:** High focus on Execution and Technical depth (DEX/INT).
* **The Scholar:** High focus on Research and Learning (INT).
* **The Athlete/Vitalist:** High focus on physical performance and recovery (VIT).

### 2.2 The Stat Framework
All tasks feed into four primary attributes:
* **INT (Intelligence):** Coding, research, deep thinking, logic.
* **DEX (Dexterity):** Precision work, hardware assembly, manual skills, "doing."
* **CHA (Charisma):** Communication, networking, marketing, social interactions.
* **VIT (Vitality):** Sleep, health, exercise, mental recovery.

### 2.3 LLM Task Orchestrator (The "Game Master")
The app must integrate an LLM (e.g., GPT-4o or Llama 3.1) to perform the following:
* **Contextual Synthesis:** Read the user's Monthly Goal (1 line) and Weekly Goal (1 line).
* **Procedural Generation:** Every morning, generate 3-5 "Daily Quests" based on:
    * Current Goals.
    * Yesterday’s incomplete/completed tasks.
    * The chosen Persona.
* **XP Assignment:** The AI must assign an XP value (e.g., 50 to 500) and a Stat Tag to each generated task based on its difficulty.
* **Dynamic Scaling:** If a user is on a "streak," the AI increases task difficulty. If the user has failed tasks recently, the AI suggests "Easy Wins."

---

## 3. Functional Requirements

### 3.1 User Onboarding & Goal Entry
* **Goal Inputs:** Simple text fields for "This Month's Vision" and "This Week's Focus."
* **Persona Selection:** A simple card-based selection UI.

### 3.2 The Daily Quest Board
* **Auto-Generation:** A "Generate Quests" button that calls the LLM.
* **Custom Tasks:** A "Quick Add" feature where the user types a task, and the AI instantly categorizes it and assigns XP.
* **Task Completion:** A checkbox/button that triggers the "Dopamine Hit" sequence.

### 3.3 The Dopamine Engine (UI/UX)
* **The "Juice":** Completion of a task must trigger a visual and auditory reward (confetti, progress bar sliding animation, "Level Up" sound).
* **XP Bars:** Visible, animated bars for each stat and an overall Character Level.
* **HP Bar (Vitality):** A daily energy bar that depletes with INT/DEX tasks and refills with VIT tasks.

### 3.4 Achievement System
* **Static Badges:** Hard-coded milestones (e.g., "7-Day Streak," "First 1000 INT XP").
* **AI-Generated Titles:** At the end of each week, the LLM analyzes completed tasks and awards a unique, descriptive title (e.g., "The Silicon Architect" or "The Relentless Executor").

---

## 4. Technical Specifications

### 4.1 Recommended Tech Stack
* **Frontend:** React.js or Next.js (for smooth state management and animations).
* **Styling:** Tailwind CSS + Framer Motion (for the "Juicy" animations).
* **Backend:** Node.js or Python (FastAPI) to handle LLM API calls.
* **Database:** Supabase or PostgreSQL (to store task history, stats, and user state).
* **LLM Integration:** OpenAI API or Groq (for fast Llama 3.1 inference).

### 4.2 Data Schema (Simplified)
* **User:** ID, Persona, Total_XP, Level, INT_XP, DEX_XP, CHA_XP, VIT_XP.
* **Tasks:** ID, User_ID, Description, XP_Value, Stat_Category, Status (Pending/Done), Created_At.
* **Goals:** User_ID, Monthly_Text, Weekly_Text.

---

## 5. Success Metrics for the PoC
1.  **Frictionless Entry:** User should spend less than 30 seconds "setting up" their day.
2.  **Accuracy:** AI-generated tasks must feel relevant to the 1-line goals provided.
3.  **Retention:** The "Level Up" animation must be satisfying enough to make the user want to check off the next task.

