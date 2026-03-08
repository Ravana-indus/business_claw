from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

setup(
	name="business_claw",
	version="1.0.0",
	description="MCP Server for ERPNext - AI Assistant Integration",
	author="Business Claw",
	author_email="admin@businessclaw.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires,
	entry_points={
		"frappe_app": [
			"business_claw = business_claw"
		]
	}
)
