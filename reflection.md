# PawPal+ Project Reflection

## 1. System Design
    - a user should get a daily plan
    - add a pet
    -keep track of tasks

**a. Initial design**

- Briefly describe your initial UML design.
The UML has four classes. Owner: time budget, start time, and preferences. Pet: animal and owns the task list. Task: priority, duration, recurrence, and a scheduled_time slot which starts empty. Scheduler takes an Owner and a Pet, sorts and filters their tasks, fits them into the time budget, and produces the final plan with an explanation.

- What classes did you include, and what responsibilities did you assign to each?
Owner and Pet are both passive data holders, Task for priority, and Scheduler for the planning logic.


**b. Design changes**

- Did your design change during implementation?
Yes

- If yes, describe at least one change and why you made it.
 Owner/Pet was not linked, but now it checks if owner.pets and pet not in owner.pets and raises a ValueError immediately, so a mismatched pair fails at construction time instead of silently producing a wrong plan.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
The scheduler considers three main factors: available time, task priority, and recurrence.

- How did you decide which constraints mattered most?
Priority is the most important because essential tasks like feeding or medication should always be handled first. Available time is the next constraint since it limits how many tasks can be completed in a day.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
The scheduler uses a greedy approach, meaning it schedules higher-priority tasks first and skips tasks that no longer fit within the remaining time.

- Why is that tradeoff reasonable for this scenario?
 This can sometimes leave out smaller tasks that could have fit together, but it keeps the scheduling process simple, predictable, and easy to understand. For a small daily pet-care schedule, this approach is practical and matches how most people naturally plan their day.

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
I used AI to help brainstorm the UML design, implement methods, debug errors, and create test cases that I might have missed. It also helped explain parts of the code that I did not fully understand after asking follow up questions.

- What kinds of prompts or questions were most helpful?
The most helpful prompts were specific questions about my code, such as how to implement sorting, recurring tasks, and conflict detection. Asking AI to explain why a solution worked was also useful.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
AI suggested rewriting part of the scheduling logic using a more compact approach, but I decided to keep the original loop because it was easier to read and understand. It also kept on giving me the diagram image instead of Mermaid source file code block.

- How did you evaluate or verify what the AI suggested?
I tested the suggestions by running the program and checking the output. I only kept changes that worked correctly and made the code easier to maintain. If I couldn't tell what it was coding then I kept on asking it follow up questions like explain me what you did, and add detailed comments.

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
I tested task completion, adding tasks to pets, sorting tasks by time, recurring tasks, conflict detection, and handling empty schedules.

- Why were these tests important?
These tests verify that the main scheduling features work correctly and help catch errors before they affect the user.

**b. Confidence**

- How confident are you that your scheduler works correctly?
I am pretty confident as All the tests have passed successfully, and the scheduler behaved as expected during manual testing.

- What edge cases would you test next if you had more time?
I would test a budget of 0 minutes, multiple pets with similar task names, and tasks that extend past midnight.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?
I am most satisfied with the scheduling system because it can prioritize tasks, stay within a time budget, and generate a clear daily plan.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?
I would improve the system so multiple pets share the same overall time budget instead of each scheduler using the full budget independently.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
I learned how to use AI as a helpful coding partner by asking it to explain code, solve specific problems, review my work, and suggest improvements. At the same time, I learned that it is important to review, test, and verify every suggestion before using it in a project.
