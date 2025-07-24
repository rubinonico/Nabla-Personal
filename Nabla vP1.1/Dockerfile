# Use the official n8n base image
FROM n8nio/n8n:latest

# Install Python and pip
# Use apt-get for Debian-based images (which n8nio/n8n is based on)
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install the 'hyperliquid' Python library
RUN pip3 install hyperliquid

# Copy your n8n workflow JSON (if it's in the same directory)
# This assumes your workflow JSON is in the root of your project
COPY nabla-v2.0-multichain-workflow.json /usr/local/lib/node_modules/n8n/workflows/

# Set the environment variable for external modules (already discussed)
ENV NODE_FUNCTION_ALLOW_EXTERNAL=buffer,@solana/web3.js

# Expose the n8n port
EXPOSE 5678

# Start n8n
CMD ["n8n", "start"]