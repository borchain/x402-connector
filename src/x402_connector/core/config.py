"""Configuration management for x402 payment processing."""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class LocalFacilitatorConfig:
    """Configuration for local (self-hosted) payment facilitator.
    
    When using local mode, your application verifies signatures and broadcasts
    transactions directly to the blockchain.
    
    Attributes:
        private_key_env: Name of environment variable containing private key
        rpc_url_env: Name of environment variable containing RPC URL
        verify_balance: Whether to check payer has sufficient ERC-20 balance
        simulate_before_send: Whether to simulate transaction before broadcasting
        wait_for_receipt: Whether to wait for transaction confirmation
    """
    
    private_key_env: str = 'X402_SIGNER_KEY'
    rpc_url_env: str = 'X402_RPC_URL'
    verify_balance: bool = False
    simulate_before_send: bool = True
    wait_for_receipt: bool = False


@dataclass
class RemoteFacilitatorConfig:
    """Configuration for remote payment facilitator service.
    
    When using remote mode, payment verification and settlement are handled
    by an external service (e.g., Coinbase's facilitator).
    
    Attributes:
        url: Base URL of the facilitator service
        headers: Optional HTTP headers to include in requests
        timeout: Request timeout in seconds
    """
    
    url: str
    headers: Optional[Dict[str, str]] = None
    timeout: int = 20


@dataclass
class X402Config:
    """Main configuration for x402 payment processing.
    
    This configuration is framework-agnostic and can be loaded from
    dictionaries, environment variables, or framework-specific config objects.
    
    Required attributes:
        network: Blockchain network (e.g., 'base', 'base-sepolia', 'polygon')
        price: Price per request (e.g., '$0.01', '1000000' for atomic units)
        pay_to_address: Ethereum address to receive payments
    
    Optional attributes:
        protected_paths: List of glob patterns for paths requiring payment
        facilitator_mode: 'local', 'remote', or 'hybrid'
        description: Human-readable description of the paid resource
        mime_type: Expected response content type
        max_timeout_seconds: Maximum validity window for payments
        discoverable: Whether to include in x402 discovery
        
    Example:
        >>> config = X402Config(
        ...     network='base',
        ...     price='$0.01',
        ...     pay_to_address='0x1234...',
        ...     protected_paths=['/api/premium/*'],
        ... )
    """
    
    # Required
    network: str
    price: str
    pay_to_address: str
    
    # Optional with defaults
    protected_paths: List[str] = field(default_factory=lambda: ['*'])
    facilitator_mode: str = 'local'
    description: str = ''
    mime_type: str = 'application/json'
    max_timeout_seconds: int = 60
    discoverable: bool = True
    
    # Facilitator configs
    local: Optional[LocalFacilitatorConfig] = None
    remote: Optional[RemoteFacilitatorConfig] = None
    
    # Advanced options
    settle_policy: str = 'block-on-failure'  # or 'log-and-continue'
    replay_cache_enabled: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
        self._set_defaults()
    
    def _validate(self):
        """Validate required fields and values."""
        if not self.network:
            raise ValueError("network is required")
        if not self.price:
            raise ValueError("price is required")
        if not self.pay_to_address:
            raise ValueError("pay_to_address is required")
        
        if self.facilitator_mode not in ('local', 'remote', 'hybrid'):
            raise ValueError(
                f"facilitator_mode must be 'local', 'remote', or 'hybrid', "
                f"got '{self.facilitator_mode}'"
            )
        
        if self.settle_policy not in ('block-on-failure', 'log-and-continue'):
            raise ValueError(
                f"settle_policy must be 'block-on-failure' or 'log-and-continue', "
                f"got '{self.settle_policy}'"
            )
    
    def _set_defaults(self):
        """Set default facilitator configs if not provided."""
        if self.facilitator_mode == 'local' and self.local is None:
            self.local = LocalFacilitatorConfig()
        
        if self.facilitator_mode == 'remote' and self.remote is None:
            raise ValueError(
                "remote facilitator config required when facilitator_mode='remote'"
            )
        
        if self.facilitator_mode == 'hybrid':
            if self.local is None:
                self.local = LocalFacilitatorConfig()
            if self.remote is None:
                raise ValueError(
                    "remote facilitator config required when facilitator_mode='hybrid'"
                )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'X402Config':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            X402Config instance
            
        Example:
            >>> config = X402Config.from_dict({
            ...     'network': 'base',
            ...     'price': '$0.01',
            ...     'pay_to_address': '0x1234...',
            ...     'local': {'verify_balance': True}
            ... })
        """
        # Make a copy to avoid mutating input
        data = config_dict.copy()
        
        # Extract nested configs
        local_config = data.pop('local', None)
        remote_config = data.pop('remote', None)
        
        # Create facilitator configs
        local = None
        if local_config is not None:
            if isinstance(local_config, LocalFacilitatorConfig):
                local = local_config
            else:
                local = LocalFacilitatorConfig(**local_config)
        
        remote = None
        if remote_config is not None:
            if isinstance(remote_config, RemoteFacilitatorConfig):
                remote = remote_config
            else:
                remote = RemoteFacilitatorConfig(**remote_config)
        
        return cls(
            local=local,
            remote=remote,
            **data
        )
    
    @classmethod
    def from_env(cls, prefix: str = 'X402_') -> 'X402Config':
        """Load configuration from environment variables.
        
        Required environment variables:
            {prefix}NETWORK - Blockchain network
            {prefix}PRICE - Price per request
            {prefix}PAY_TO_ADDRESS - Payment recipient address
        
        Optional environment variables:
            {prefix}PROTECTED_PATHS - Comma-separated path patterns
            {prefix}FACILITATOR_MODE - 'local', 'remote', or 'hybrid'
            {prefix}DESCRIPTION - Resource description
            And more...
        
        Args:
            prefix: Prefix for environment variable names
            
        Returns:
            X402Config instance
            
        Raises:
            ValueError: If required environment variables are missing
            
        Example:
            >>> os.environ['X402_NETWORK'] = 'base'
            >>> os.environ['X402_PRICE'] = '$0.01'
            >>> os.environ['X402_PAY_TO_ADDRESS'] = '0x1234...'
            >>> config = X402Config.from_env()
        """
        network = os.getenv(f'{prefix}NETWORK')
        price = os.getenv(f'{prefix}PRICE')
        pay_to = os.getenv(f'{prefix}PAY_TO_ADDRESS')
        
        if not all([network, price, pay_to]):
            missing = []
            if not network:
                missing.append(f'{prefix}NETWORK')
            if not price:
                missing.append(f'{prefix}PRICE')
            if not pay_to:
                missing.append(f'{prefix}PAY_TO_ADDRESS')
            
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )
        
        # Parse protected paths
        paths_str = os.getenv(f'{prefix}PROTECTED_PATHS', '*')
        protected_paths = [p.strip() for p in paths_str.split(',')]
        
        return cls(
            network=network,
            price=price,
            pay_to_address=pay_to,
            protected_paths=protected_paths,
            facilitator_mode=os.getenv(f'{prefix}FACILITATOR_MODE', 'local'),
            description=os.getenv(f'{prefix}DESCRIPTION', ''),
            mime_type=os.getenv(f'{prefix}MIME_TYPE', 'application/json'),
            max_timeout_seconds=int(os.getenv(f'{prefix}MAX_TIMEOUT_SECONDS', '60')),
            discoverable=os.getenv(f'{prefix}DISCOVERABLE', 'true').lower() == 'true',
            settle_policy=os.getenv(f'{prefix}SETTLE_POLICY', 'block-on-failure'),
            replay_cache_enabled=os.getenv(
                f'{prefix}REPLAY_CACHE_ENABLED', 'false'
            ).lower() == 'true',
        )

