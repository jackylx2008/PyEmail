# 定义项目根目录为当前目录
$projectRoot = "."

# 创建 parsers 目录及其文件
$parsersDir = "$projectRoot\parsers"
New-Item -ItemType Directory -Path $parsersDir
New-Item -ItemType File -Path "$parsersDir\eml_parser.py"
New-Item -ItemType File -Path "$parsersDir\body_parser.py"
New-Item -ItemType File -Path "$parsersDir\attachment.py"

# 创建 database 目录及其文件
$databaseDir = "$projectRoot\database"
New-Item -ItemType Directory -Path $databaseDir
New-Item -ItemType File -Path "$databaseDir\db_init.py"
New-Item -ItemType File -Path "$databaseDir\db_operations.py"

# 创建 utils 目录及其文件
$utilsDir = "$projectRoot\utils"
New-Item -ItemType Directory -Path $utilsDir
New-Item -ItemType File -Path "$utilsDir\config.py"
New-Item -ItemType File -Path "$utilsDir\logger.py"

# 创建 attachments 目录
New-Item -ItemType Directory -Path "$projectRoot\attachments"

# 创建 logs 目录及其日志文件
$logsDir = "$projectRoot\logs"
New-Item -ItemType Directory -Path $logsDir
New-Item -ItemType File -Path "$logsDir\app.log"

# 创建配置文件
New-Item -ItemType File -Path "$projectRoot\config.json"

# 创建 SQLite 数据库文件
New-Item -ItemType File -Path "$projectRoot\database.db"

# 创建依赖库文件
New-Item -ItemType File -Path "$projectRoot\requirements.txt"

# 创建主程序入口文件
New-Item -ItemType File -Path "$projectRoot\main.py"

Write-Host "项目结构和文件已成功创建在当前目录！"
