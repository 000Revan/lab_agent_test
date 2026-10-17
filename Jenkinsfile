pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    stages {
        stage('检出测试仓库') {
            steps {
                dir('tests') {
                    checkout scm
                }
            }
        }

        stage('检出后端仓库') {
            steps {
                dir('backend') {
                    checkout(
                        poll: true,
                        changelog: true,
                        scm: [
                            $class: 'GitSCM',
                            branches: [[name: '*/master']],
                            userRemoteConfigs: [[
                                url: 'https://github.com/000Revan/lab_agent_backend.git',
                                credentialsId: 'github-read'
                            ]]
                        ]
                    )
                }
            }
        }

        stage('验证检出结果') {
            steps {
                powershell '''
                    $ErrorActionPreference = 'Stop'

                    if (-not (Test-Path 'backend/requirements.txt')) {
                        throw '未找到后端requirements.txt，请检查仓库结构'
                    }

                    if (-not (Test-Path 'tests/run.py')) {
                        throw '未找到测试run.py，请检查仓库结构'
                    }

                    Write-Host '两个仓库检出成功'
                '''
            }
        }
    }
}