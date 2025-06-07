#!/usr/bin/env python3
"""
Unit tests for the config module.
"""

import pytest
import tempfile
import configparser
from pathlib import Path
from unittest.mock import patch, mock_open

from slurm_plot.config import (
    load_config, get_config_value, create_default_config,
    validate_config, DEFAULT_CONFIG
)


class TestConfig:
    """Test cases for configuration functions."""
    
    def test_load_config_default(self):
        """Test loading default configuration."""
        config = load_config()
        
        # Should return default configuration
        assert 'slurm' in config
        assert 'processing' in config
        assert 'plotting' in config
        assert 'output' in config
        
        # Check specific default values
        assert config['slurm']['sacct_command'] == 'sacct'
        assert config['processing']['memory_unit'] == 'GB'
        assert config['plotting']['dpi'] == '300'
        
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        # Create a temporary config file
        config_content = """
[slurm]
sacct_command = custom_sacct
timeout = 60

[plotting]
dpi = 150
style = ggplot
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write(config_content)
            config_path = f.name
            
        try:
            config = load_config(config_path)
            
            # Should have custom values
            assert config['slurm']['sacct_command'] == 'custom_sacct'
            assert config['slurm']['timeout'] == '60'
            assert config['plotting']['dpi'] == '150'
            assert config['plotting']['style'] == 'ggplot'
            
            # Should still have default values for unspecified options
            assert config['processing']['memory_unit'] == 'GB'
            
        finally:
            Path(config_path).unlink()
            
    def test_load_config_file_not_found(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config('/nonexistent/config.ini')
            
    @patch('configparser.ConfigParser.read')
    @patch('pathlib.Path.exists')
    def test_load_config_standard_locations(self, mock_exists, mock_read):
        """Test loading config from standard locations."""
        mock_exists.return_value = True
        
        config = load_config()
        
        # Should have attempted to read from the existing standard location
        mock_read.assert_called()
        
    def test_get_config_value(self):
        """Test getting configuration values with type conversion."""
        config = {
            'section1': {
                'string_value': 'test',
                'int_value': '42',
                'float_value': '3.14',
                'bool_true': 'true',
                'bool_false': 'false',
                'bool_1': '1',
                'bool_0': '0'
            }
        }
        
        # Test string values
        assert get_config_value(config, 'section1', 'string_value') == 'test'
        assert get_config_value(config, 'section1', 'missing', 'default') == 'default'
        
        # Test integer conversion
        assert get_config_value(config, 'section1', 'int_value', 0) == 42
        assert get_config_value(config, 'section1', 'missing', 10) == 10
        
        # Test float conversion
        assert get_config_value(config, 'section1', 'float_value', 0.0) == 3.14
        assert get_config_value(config, 'section1', 'missing', 1.0) == 1.0
        
        # Test boolean conversion
        assert get_config_value(config, 'section1', 'bool_true', False) is True
        assert get_config_value(config, 'section1', 'bool_false', True) is False
        assert get_config_value(config, 'section1', 'bool_1', False) is True
        assert get_config_value(config, 'section1', 'bool_0', True) is False
        assert get_config_value(config, 'section1', 'missing', True) is True
        
    def test_get_config_value_invalid_conversion(self):
        """Test handling of invalid type conversions."""
        config = {
            'section1': {
                'invalid_int': 'not_a_number',
                'invalid_float': 'not_a_float'
            }
        }
        
        # Should return default values for invalid conversions
        assert get_config_value(config, 'section1', 'invalid_int', 42) == 42
        assert get_config_value(config, 'section1', 'invalid_float', 3.14) == 3.14
        
    def test_get_config_value_missing_section(self):
        """Test handling of missing configuration sections."""
        config = {'section1': {'key1': 'value1'}}
        
        # Should return default for missing section
        assert get_config_value(config, 'missing_section', 'key', 'default') == 'default'
        
    def test_create_default_config(self):
        """Test creating default configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'test_config.ini'
            
            create_default_config(str(config_path))
            
            # Check that file was created
            assert config_path.exists()
            
            # Check that it contains expected sections
            parser = configparser.ConfigParser()
            parser.read(config_path)
            
            assert 'slurm' in parser.sections()
            assert 'processing' in parser.sections()
            assert 'plotting' in parser.sections()
            assert 'output' in parser.sections()
            
            # Check specific values
            assert parser['slurm']['sacct_command'] == 'sacct'
            assert parser['processing']['memory_unit'] == 'GB'
            
    def test_create_default_config_nested_directory(self):
        """Test creating default config in nested directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'nested' / 'dir' / 'config.ini'
            
            create_default_config(str(config_path))
            
            # Check that nested directories were created
            assert config_path.exists()
            assert config_path.parent.exists()
            
    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        config = DEFAULT_CONFIG.copy()
        
        assert validate_config(config) is True
        
    def test_validate_config_missing_section(self):
        """Test validation with missing section."""
        config = DEFAULT_CONFIG.copy()
        del config['slurm']
        
        assert validate_config(config) is False
        
    def test_validate_config_invalid_timeout(self):
        """Test validation with invalid timeout value."""
        config = DEFAULT_CONFIG.copy()
        config['slurm']['timeout'] = '0'  # Invalid: should be > 0
        
        assert validate_config(config) is False
        
        config['slurm']['timeout'] = '-5'  # Invalid: negative
        assert validate_config(config) is False
        
        config['slurm']['timeout'] = 'invalid'  # Invalid: not a number
        assert validate_config(config) is False
        
    def test_validate_config_invalid_dpi(self):
        """Test validation with invalid DPI value."""
        config = DEFAULT_CONFIG.copy()
        config['plotting']['dpi'] = '0'  # Invalid: should be > 0
        
        assert validate_config(config) is False
        
        config['plotting']['dpi'] = 'invalid'  # Invalid: not a number
        assert validate_config(config) is False
        
    def test_validate_config_invalid_quality(self):
        """Test validation with invalid quality value."""
        config = DEFAULT_CONFIG.copy()
        config['output']['quality'] = '101'  # Invalid: should be <= 100
        
        assert validate_config(config) is False
        
        config['output']['quality'] = '-1'  # Invalid: should be >= 0
        assert validate_config(config) is False
        
    def test_validate_config_invalid_thresholds(self):
        """Test validation with invalid efficiency thresholds."""
        config = DEFAULT_CONFIG.copy()
        
        # Invalid CPU efficiency threshold
        config['processing']['cpu_efficiency_threshold'] = '1.5'  # > 1
        assert validate_config(config) is False
        
        config['processing']['cpu_efficiency_threshold'] = '-0.1'  # < 0
        assert validate_config(config) is False
        
        # Reset and test memory efficiency threshold
        config = DEFAULT_CONFIG.copy()
        config['processing']['memory_efficiency_threshold'] = '2.0'  # > 1
        assert validate_config(config) is False
        
        config['processing']['memory_efficiency_threshold'] = '-0.5'  # < 0
        assert validate_config(config) is False
        
    def test_validate_config_missing_keys(self):
        """Test validation with missing configuration keys."""
        config = DEFAULT_CONFIG.copy()
        del config['slurm']['timeout']
        
        # Should return False due to missing key
        assert validate_config(config) is False
        
    def test_default_config_structure(self):
        """Test that DEFAULT_CONFIG has expected structure."""
        # Check that all required sections exist
        required_sections = ['slurm', 'processing', 'plotting', 'output']
        for section in required_sections:
            assert section in DEFAULT_CONFIG
            
        # Check that sections have expected keys
        assert 'sacct_command' in DEFAULT_CONFIG['slurm']
        assert 'default_fields' in DEFAULT_CONFIG['slurm']
        assert 'memory_unit' in DEFAULT_CONFIG['processing']
        assert 'dpi' in DEFAULT_CONFIG['plotting']
        assert 'quality' in DEFAULT_CONFIG['output']
        
    def test_config_type_consistency(self):
        """Test that configuration values have consistent types."""
        config = load_config()
        
        # All values should be strings (as they come from ConfigParser)
        for section_name, section in config.items():
            for key, value in section.items():
                assert isinstance(value, str), f"{section_name}.{key} should be string, got {type(value)}"
                

if __name__ == '__main__':
    pytest.main([__file__])