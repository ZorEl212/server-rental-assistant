# Check if python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 is not installed. Please install python3"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "Pip3 is not installed. Please install pip3"
    exit 1
fi

# Check if python3-venv is installed
if ! dpkg -s python3-venv &> /dev/null
then
    echo "python3-venv is not installed. Please install python3-venv"
    exit 1
fi

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install the required packages
pip3 install -r requirements.txt

# Deactivate the virtual environment
deactivate

# Install redis server
sudo apt-get install lsb-release curl gpg
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install redis -y

echo -e "\e[32mSetup complete. Run 'source venv/bin/activate' to activate the virtual environment\e[0m"
