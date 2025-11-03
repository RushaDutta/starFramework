import pandas as pd
import random
import faker

# Initialize Faker
fake = faker.Faker()

# Define constants
num_entries = 150
authors = [fake.name() for _ in range(20)]
stakeholders = [fake.name() for _ in range(40)]

# Generate dummy data
data = []
for i in range(1, num_entries + 1):
    user_story_id = f"US-{1000 + i}"
    jira_id = f"JIRA-{random.randint(1000, 9999)}"
    title = fake.sentence(nb_words=6).replace(".", "")
    description = fake.paragraph(nb_sentences=3)
    author = random.choice(authors)
    stakeholder_list = ", ".join(random.sample(stakeholders, k=random.randint(1, 3)))

    # Other fields left blank
    data.append([
        user_story_id, jira_id, title, description, author, stakeholder_list,
        "", "", "", "", "", "", "", "", "", "", "", "", ""
    ])

# Define columns
columns = [
    "UserStoryID", "JiraID", "Title", "Description", "Author", "Stakeholders",
    "PM_Comments", "Developer_Comments", "QA_Comments", "Risk", "Dependencies",
    "Priority", "Rationale", "TradeOffs", "Outcome", "Status",
    "ReviewedBy", "DiscussionDate", "FinalDecision"
]

# Create DataFrame
df = pd.DataFrame(data, columns=columns)

# Save as CSV
df.to_csv("dummy_user_stories.csv", index=False)
print("✅ dummy_user_stories.csv created successfully with only key fields populated!")
