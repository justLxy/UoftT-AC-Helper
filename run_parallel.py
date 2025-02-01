import subprocess

num_instances = 3  # Adjust based on how many bots you want to run
processes = []

for _ in range(num_instances):
    p = subprocess.Popen(["python", "bot.py"])
    processes.append(p)

# Wait for all processes to complete (optional)
for p in processes:
    p.wait()
