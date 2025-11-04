"""Configuration management for x402 payment processing on Solana."""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class X402Config:
    """Configuration for x402 payment processing on Solana.
    
    Required:
        pay_to_address: Solana address where payments are received (base58 format)
    
    Optional:
        price: Default price per request. Default: '$0.01'
        network: Solana network. Default: 'solana-mainnet'
                 Options: 'solana-mainnet', 'solana-devnet', 'solana-testnet'
        protected_paths: URL paths requiring payment. Default: ['*'] (all paths)
        description: Human-readable description. Default: 'API Access'
        rpc_url: Custom RPC URL. Default: Uses public RPC based on network
        signer_key_env: Environment variable for private key. Default: 'X402_SIGNER_KEY'
        max_timeout_seconds: Payment validity window. Default: 60
        verify_balance: Check sender has sufficient funds. Default: False
        wait_for_confirmation: Wait for transaction confirmation. Default: False
        debug_mode: If True, simulate transactions instead of broadcasting. Default: False
    
    Example:
        >>> config = X402Config(
        ...     pay_to_address='YourSolanaAddressHere1234567890123456789012',
        ...     price='$0.01',
        ...     network='solana-devnet',
        ... )
    """
    
    # Required
    pay_to_address: str
    
    # Optional with defaults
    price: str = '$0.01'
    network: str = 'solana-mainnet'
    protected_paths: List[str] = field(default_factory=lambda: ['*'])
    description: str = 'API Access'
    mime_type: str = 'application/json'
    rpc_url: Optional[str] = None
    signer_key_env: str = 'X402_SIGNER_KEY'
    max_timeout_seconds: int = 60
    verify_balance: bool = False
    wait_for_confirmation: bool = False
    discoverable: bool = True
    debug_mode: bool = True  # Set False to broadcast REAL transactions (requires proper setup)
    use_durable_nonce: bool = False  # Set True to use durable nonces (no blockhash expiry!)
    nonce_account_env: str = 'X402_NONCE_ACCOUNT'  # Env var for nonce account address
    
    # Settlement options
    settle_policy: str = 'block-on-failure'  # or 'log-and-continue'
    replay_cache_enabled: bool = True
    
    # Internal configs (for facilitator)
    local: Optional[Dict[str, Any]] = None
    facilitator_mode: str = 'local'  # Always local for Solana
    
    def __post_init__(self):
        """Validate and set up configuration."""
        self._validate()
        self._setup_local_config()
    
    def _validate(self):
        """Validate required fields."""
        if not self.pay_to_address:
            raise ValueError("pay_to_address is required")
        
        if not self.price:
            raise ValueError("price is required")
        
        # Validate network
        valid_networks = ['solana-mainnet', 'solana-devnet', 'solana-testnet']
        if self.network not in valid_networks:
            raise ValueError(
                f"network must be one of {valid_networks}, got '{self.network}'"
            )
        
        # Validate address format (basic check for base58)
        if not self.pay_to_address or len(self.pay_to_address) < 32:
            raise ValueError(
                "pay_to_address must be a valid Solana address (base58 format)"
            )
    
    def _setup_local_config(self):
        """Setup local facilitator configuration."""
        if self.local is None:
            # Get RPC URL
            rpc_url = self.rpc_url
            if not rpc_url:
                # Use default based on network
                rpc_urls = {
                    'solana-mainnet': 'https://api.mainnet-beta.solana.com',
                    'solana-devnet': 'https://api.devnet.solana.com',
                    'solana-testnet': 'https://api.testnet.solana.com',
                }
                rpc_url = rpc_urls.get(self.network, 'https://api.devnet.solana.com')
            
            self.local = {
                'private_key_env': self.signer_key_env,
                'rpc_url': rpc_url,
                'verify_balance': self.verify_balance,
                'wait_for_confirmation': self.wait_for_confirmation,
                'debug_mode': self.debug_mode,
                'use_durable_nonce': self.use_durable_nonce,
                'nonce_account_env': self.nonce_account_env,
            }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'X402Config':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            X402Config instance
            
        Example:
            >>> config = X402Config.from_dict({
            ...     'pay_to_address': 'DYw8j...',
            ...     'price': '$0.01',
            ...     'network': 'solana-devnet',
            ... })
        """
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls, prefix: str = 'X402_') -> 'X402Config':
        """Load configuration from environment variables.
        
        Required:
            {prefix}PAY_TO_ADDRESS - Solana address for payments
        
        Optional:
            {prefix}PRICE - Price per request (default: '$0.01')
            {prefix}NETWORK - Solana network (default: 'solana-mainnet')
            {prefix}RPC_URL - Custom RPC URL
            {prefix}SIGNER_KEY - Private key (used at runtime, not for config)
            {prefix}PROTECTED_PATHS - Comma-separated paths
        
        Args:
            prefix: Prefix for environment variable names
            
        Returns:
            X402Config instance
            
        Example:
            >>> os.environ['X402_PAY_TO_ADDRESS'] = 'DYw8j...'
            >>> config = X402Config.from_env()
        """
        pay_to = os.getenv(f'{prefix}PAY_TO_ADDRESS')
        if not pay_to:
            raise ValueError(
                f"Missing required environment variable: {prefix}PAY_TO_ADDRESS"
            )
        
        # Parse protected paths
        paths_str = os.getenv(f'{prefix}PROTECTED_PATHS', '*')
        protected_paths = [p.strip() for p in paths_str.split(',')]
        
        return cls(
            pay_to_address=pay_to,
            price=os.getenv(f'{prefix}PRICE', '$0.01'),
            network=os.getenv(f'{prefix}NETWORK', 'solana-mainnet'),
            protected_paths=protected_paths,
            description=os.getenv(f'{prefix}DESCRIPTION', 'API Access'),
            rpc_url=os.getenv(f'{prefix}RPC_URL'),
            signer_key_env=f'{prefix}SIGNER_KEY',
            max_timeout_seconds=int(os.getenv(f'{prefix}MAX_TIMEOUT_SECONDS', '60')),
            verify_balance=os.getenv(f'{prefix}VERIFY_BALANCE', 'false').lower() == 'true',
            wait_for_confirmation=os.getenv(
                f'{prefix}WAIT_FOR_CONFIRMATION', 'false'
            ).lower() == 'true',
        )
