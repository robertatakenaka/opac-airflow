# Prepara Sincronizacao com Kernel
# Copia Scilista para diretorio do Escalonador
# Copia Pacotes da lista para diretorio do Escalonador

# SCILISTA_PATH: path do arquivo scilista que sera usado no processamento iniciado pelo GeraPadrao
# XC_SPS_PACKAGES: path do diretório com todos os pacotes gerados pelo XC
# XC_KERNEL_GATE: path do diretório para copia dos pacotes como estao no momento que o processamento do GeraPadrao e iniciado


echo ===============
echo
echo "Prepara Sincronizacao com o Kernel..."
echo "Copiando pacotes SPS para a área do Escalonador"
echo
echo ===============

SCILISTA_PATH_TMP=/tmp/scilista.lst
cp $SCILISTA_PATH $SCILISTA_PATH_TMP
if [ -e $SCILISTA_PATH_TMP ]; then
    cat $SCILISTA_PATH_TMP | sort -u > $SCILISTA_PATH

if [ ! -z ${SCILISTA_PATH+x} ] && [ ! -z ${XC_SPS_PACKAGES+x} ] && [ ! -z ${XC_KERNEL_GATE+x} ];
then
    while read LINE; do
        ACRON="$(echo $LINE | cut -f1 -d ' ')"
        ISSUE="$(echo $LINE | cut -f2 -d ' ')"
        DEL_COMMAND="$(echo $LINE | cut -f3 -d ' ')"
        echo
        echo "ACRON: $ACRON"
        echo "ISSUE: $ISSUE"
        echo

        if [[ $(tr '[:upper:]' '[:lower:]' <<< "$DEL_COMMAND") = del ]];
        then
            echo
            echo "Package to delete: ${ACRON}_${ISSUE}"
            echo
        else
            PACK_NAME="${XC_SPS_PACKAGES}/*${ACRON}_${ISSUE}.zip"
            if [ -e ${PACK_NAME} ]
            then
                echo
                echo "Move pack ${PACK_NAME} to ${XC_KERNEL_GATE} ..."
                echo
                mv ${PACK_NAME} ${XC_KERNEL_GATE}
            else
                if [[ "$ISSUE" == *"ahead"* ]]
                then
                    echo
                    echo "WARNING: Not found ${PACK_NAME} to move"
                    echo
                else
                    echo
                    echo "ERROR: ${PACK_NAME} is expected to exist to be moved to ${XC_KERNEL_GATE}"
                    echo
                fi

        fi

    done < $SCILISTA_PATH

    echo
    echo "Copiando scilista de $SCILISTA_PATH para a área do Escalonador em ${XC_KERNEL_GATE}"
    echo

    cp ${SCILISTA_PATH} ${XC_KERNEL_GATE}

    echo
    echo "SPS Packages and Scilista copied successfully!"
    echo
else
    echo
    echo "SCILISTA_PATH, XC_SPS_PACKAGES e XC_KERNEL_GATE sao obrigatorias para a Syncronizacao com o Kernel."
    echo "Verifique se as tres variaveis estao configuradas."
    echo "A execucao do proc seguira sem o Kernel."
    echo
    echo ===============
fi
